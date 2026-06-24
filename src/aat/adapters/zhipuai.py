"""ZhipuAIAdapter — 智谱AI GLM API integration."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

from aat.adapters.base import AIAdapter
from aat.adapters.prompts import (
    _SYSTEM_ANALYZE_DOCUMENT,
    _SYSTEM_ANALYZE_FAILURE,
    _SYSTEM_GENERATE_FIX,
    _SYSTEM_GENERATE_SCENARIOS,
)
from aat.core.exceptions import AdapterError
from aat.core import (
    AnalysisResult,
    FileChange,
    FixResult,
    Scenario,
    Severity,
)

if TYPE_CHECKING:
    from aat.core import AIConfig, TestResult

logger = logging.getLogger(__name__)

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
        self.base_url = "https://open.bigmodel.cn/api/coding/paas/v4/"
        # 支持的模型：glm-4.7, glm-4.7, glm-4, glm-4-plus, glm-4-0520, glm-5.1
        self.model = config.model or "glm-4.7"  # 默认使用GLM-4.7（最新推荐）
        
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
        # Find failed step
        failed_step_result = next(
            (s for s in test_result.steps if s.status.value == "failed"),
            None
        )

        if failed_step_result:
            failed_step_num = failed_step_result.step
            failed_action = failed_step_result.action.value
            failed_desc = failed_step_result.description
            failed_error = failed_step_result.error_message or "Unknown error"
        else:
            failed_step_num = 0
            failed_action = "unknown"
            failed_desc = "Unknown step"
            failed_error = test_result.steps[0].error_message if test_result.steps else "No error details"

        # 构建失败分析消息
        content = f"""Test failed:
Scenario: {test_result.scenario_name}
Step {failed_step_num} ({failed_action}): {failed_desc}
Error: {failed_error}

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

        # 解析响应（支持JSON和YAML格式）
        # 清理可能的markdown代码块
        cleaned_response = response.strip()
        if cleaned_response.startswith("```"):
            # 移除markdown代码块标记
            lines = cleaned_response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]  # 移除首行
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]  # 移除末行
            cleaned_response = "\n".join(lines)

        scenarios_data = None
        parse_error = None

        # 先尝试JSON解析
        try:
            scenarios_data = json.loads(cleaned_response)
        except (json.JSONDecodeError, ValueError) as je:
            parse_error = je

        # 如果JSON失败，尝试YAML解析
        if scenarios_data is None:
            try:
                scenarios_data = yaml.safe_load(cleaned_response)
            except Exception as ye:
                parse_error = ye if parse_error is None else parse_error

        if scenarios_data is None:
            raise AdapterError(f"Failed to parse scenarios: {parse_error}") from parse_error

        if not isinstance(scenarios_data, list):
            raise AdapterError("Expected list of scenarios")

        # 转换为Scenario对象（使用 Pydantic 验证）
        scenarios = []
        for i, item in enumerate(scenarios_data):
            # 确保有默认 id
            if "id" not in item:
                item["id"] = f"scenario-{i}"
            scenario = Scenario.model_validate(item)
            scenarios.append(scenario)
        return scenarios

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
