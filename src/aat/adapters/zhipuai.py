"""ZhipuAIAdapter — 智谱AI GLM API integration."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

from aat.adapters.base import AIAdapter
from aat.core.exceptions import AdapterError
from aat.core.models import (
    AnalysisResult,
    FileChange,
    FixResult,
    Scenario,
    Severity,
)

if TYPE_CHECKING:
    from aat.core.models import AIConfig, TestResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates (shared with ClaudeAdapter / OpenAIAdapter)
# ---------------------------------------------------------------------------

_SYSTEM_ANALYZE_FAILURE = """\
You are an expert QA engineer. Analyze the following test failure and return \
a JSON object with these fields:
- "cause": a concise description of the root cause
- "suggestion": an actionable fix suggestion
- "severity": one of "critical", "warning", "info"
- "related_files": a list of file paths likely involved

Return ONLY valid JSON, no markdown fences."""

_SYSTEM_GENERATE_FIX = """\
You are an expert software engineer. Given a failure analysis and source files, \
propose a code fix. Return a JSON object with:
- "description": short description of the fix
- "files_changed": list of objects with "path", "original", "modified", "description"
- "confidence": float 0.0-1.0

Return ONLY valid JSON, no markdown fences."""

_SYSTEM_GENERATE_SCENARIOS = """\
You are an expert test automation engineer. Analyze the following specification \
and generate test scenarios in YAML format. Each scenario should have:
- id: unique identifier
- name: descriptive name
- description: what is being tested
- url: starting URL
- steps: list of test steps with action, selector, value (if applicable), \
  description, and assert (if applicable)

Return ONLY valid YAML, no markdown fences.
Each step action can be: navigate, click, type, wait, assert_text, assert_visible.

Example:
```yaml
- id: login-001
  name: User Login
  description: Test successful user login
  url: https://example.com/login
  steps:
    - action: navigate
      value: https://example.com/login
      description: Navigate to login page
    - action: type
      selector: '#username'
      value: testuser
      description: Enter username
    - action: click
      selector: '#login-button'
      description: Click login button
    - action: assert_text
      value: Welcome
      description: Verify successful login
```"""

_SYSTEM_ANALYZE_DOCUMENT = """\
You are an expert business analyst. Analyze the following specification document \
and extract structured information. Return a JSON object with:
- "screens": list of screens/pages mentioned
- "elements": list of UI elements with selectors
- "flows": list of user flows or business processes

Return ONLY valid JSON, no markdown fences."""

# ---------------------------------------------------------------------------
# ZhipuAIAdapter
# ---------------------------------------------------------------------------


class ZhipuAIAdapter(AIAdapter):
    """智谱AI GLM API adapter.

    Uses OpenAI-compatible API with ZhipuAI-specific base URL and models.
    """

    def __init__(self, config: AIConfig) -> None:
        """Initialize ZhipuAI adapter.

        Args:
            config: AIConfig with api_key and optional model/base_url.
        """
        if not config.api_key:
            raise AdapterError("ZhipuAI API key is required")

        # 智谱AI默认配置（base_url是固定的，不由AIConfig提供）
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/"
        # 支持的模型：glm-4-flash, glm-4, glm-4-plus, glm-4-0520, glm-4.7, glm-5.1
        self.model = config.model or "glm-4-flash"  # 默认使用GLM-4-Flash（性价比高）
        
        # 初始化OpenAI客户端（智谱AI兼容OpenAI API）
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=self.base_url,
        )
        
        logger.info(f"ZhipuAIAdapter initialized with model {self.model}")

    async def _call_api(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Call ZhipuAI API.

        Args:
            messages: Chat messages.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            Response content text.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise AdapterError(f"ZhipuAI API call failed: {e}") from e

    async def analyze_failure(
        self,
        test_result: TestResult,
        screenshots: list[bytes] | None = None,
    ) -> AnalysisResult:
        """Analyze test failure cause.

        Args:
            test_result: Failed test result.
            screenshots: Optional screenshots (not used by text-only API).

        Returns:
            AnalysisResult with cause, suggestion, severity.
        """
        # 构建失败分析消息
        content = f"""Test failed:
Scenario: {test_result.scenario_name}
Step {test_result.failed_step}: {test_result.step_description}
Error: {test_result.error_message}

Please analyze this failure."""

        messages = [
            {"role": "system", "content": _SYSTEM_ANALYZE_FAILURE},
            {"role": "user", "content": content},
        ]

        response = await self._call_api(messages, max_tokens=2048)

        # 解析JSON响应
        try:
            data = json.loads(response)
            return AnalysisResult(
                cause=data.get("cause", "Unknown cause"),
                suggestion=data.get("suggestion", "No suggestion"),
                severity=Severity(data.get("severity", "info")),
                related_files=data.get("related_files", []),
            )
        except json.JSONDecodeError as e:
            raise AdapterError(f"Failed to parse analysis response: {e}") from e

    async def generate_fix(
        self,
        analysis: AnalysisResult,
        source_files: dict[str, str],
    ) -> FixResult:
        """Generate code fix based on analysis.

        Args:
            analysis: Failure analysis result.
            source_files: {file_path: file_content} dict.

        Returns:
            FixResult with description, changed files, confidence.
        """
        # 构建修复生成消息
        content = f"""Failure Analysis:
Cause: {analysis.cause}
Suggestion: {analysis.suggestion}

Source Files:
{json.dumps(source_files, indent=2)[:10000]}

Please propose a fix."""

        messages = [
            {"role": "system", "content": _SYSTEM_GENERATE_FIX},
            {"role": "user", "content": content},
        ]

        response = await self._call_api(messages, max_tokens=4096)

        # 解析JSON响应
        try:
            data = json.loads(response)
            files_changed = [
                FileChange(
                    path=fc["path"],
                    original=fc.get("original", ""),
                    modified=fc["modified"],
                    description=fc.get("description", ""),
                )
                for fc in data.get("files_changed", [])
            ]
            return FixResult(
                description=data.get("description", "No description"),
                files_changed=files_changed,
                confidence=data.get("confidence", 0.5),
            )
        except json.JSONDecodeError as e:
            raise AdapterError(f"Failed to parse fix response: {e}") from e

    async def generate_scenarios(
        self,
        document_text: str,
        images: list[bytes] | None = None,
        *,
        system_prompt: str | None = None,
    ) -> list[Scenario]:
        """Generate test scenarios from document analysis.

        Args:
            document_text: Spec/design guide text.
            images: Images (not used by text-only API).
            system_prompt: Optional system prompt override.

        Returns:
            List of generated Scenario objects.
        """
        import yaml

        content = f"""Analyze this specification and generate test scenarios:

{document_text[:8000]}

Generate 3-5 test scenarios covering main user flows."""

        messages = [
            {"role": "system", "content": system_prompt or _SYSTEM_GENERATE_SCENARIOS},
            {"role": "user", "content": content},
        ]

        response = await self._call_api(messages, max_tokens=4096)

        # 解析YAML响应
        try:
            scenarios_data = yaml.safe_load(response)
            if not isinstance(scenarios_data, list):
                raise AdapterError("Expected list of scenarios")

            # 转换为Scenario对象（简化版，实际需要完整模型）
            scenarios = []
            for i, item in enumerate(scenarios_data):
                scenario = Scenario(
                    id=item.get("id", f"scenario-{i}"),
                    name=item.get("name", f"Scenario {i}"),
                    description=item.get("description", ""),
                    url=item.get("url", ""),
                    steps=item.get("steps", []),
                )
                scenarios.append(scenario)
            return scenarios
        except Exception as e:
            raise AdapterError(f"Failed to parse scenarios: {e}") from e

    async def verify_step(
        self,
        screenshot: bytes,
        step_num: int,
        action: str,
        description: str,
    ) -> tuple[bool, str]:
        """Verify step by analyzing screenshot (not supported by text-only API).

        Args:
            screenshot: Screenshot bytes.
            step_num: Step number.
            action: Action type.
            description: Step description.

        Returns:
            (passed, reason) tuple.

        Note:
            ZhipuAI text-only API does not support vision. Use a different adapter
            or implement custom vision integration.
        """
        raise NotImplementedError(
            "ZhipuAI text-only API does not support vision. "
            "Use a different adapter or implement custom vision integration."
        )

    async def analyze_document(
        self,
        document_text: str,
        images: list[bytes] | None = None,
    ) -> dict[str, Any]:
        """Analyze spec document to extract structured information.

        Args:
            document_text: Specification text.
            images: Images (not used).

        Returns:
            dict with screens, elements, flows.
        """
        content = f"""Analyze this specification document:

{document_text[:8000]}

Extract screens, UI elements, and user flows."""

        messages = [
            {"role": "system", "content": _SYSTEM_ANALYZE_DOCUMENT},
            {"role": "user", "content": content},
        ]

        response = await self._call_api(messages, max_tokens=4096)

        # 解析JSON响应
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise AdapterError(f"Failed to parse document analysis: {e}") from e
