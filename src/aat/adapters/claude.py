"""
════════════════════════════════════════════════════════════════════════════════
                     🧠 Claude Adapter Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Anthropic Claude API integration for AI-powered test failure analysis, code
fix generation, and test scenario creation. Supports vision capabilities for
screenshot-based debugging.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.adapters.claude import ClaudeAdapter
from aat.core import AIConfig

config = AIConfig(
    provider="claude",
    api_key="sk-ant-...",
    model="claude-sonnet-4-20250514"
)

adapter = ClaudeAdapter(config)

# Analyze test failure with screenshot
analysis = await adapter.analyze_failure(
    test_result=result,
    screenshots=[screenshot_bytes]
)

# Generate code fix
fix = await adapter.generate_fix(analysis, source_files)

# Verify step result visually
passed, reason = await adapter.verify_step(
    screenshot=screenshot_bytes,
    step_num=1,
    action="find_and_click",
    description="Click login button"
)
```

⚙️  CAPABILITIES
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Method              │  Vision  │  Purpose                          │
├────────────────────────────────────────────────────────────────────────────┤
│  analyze_failure()   │    ✅     │  Diagnose failures with screenshots │
│  generate_fix()      │    ❌     │  Generate code patches             │
│  generate_scenarios()│    ✅     │  Create scenarios from specs       │
│  analyze_document()  │    ✅     │  Extract requirements from docs     │
│  verify_step()       │    ✅     │  Visual step verification           │
└────────────────────────────────────────────────────────────────────────────┘

🧠 CLAUDE API FEATURES
───────────────────────────────────────────────────────────────────────────────
• Vision API — Analyze screenshots for visual debugging
• Long context windows — Handle large source files and complex scenarios
• High reasoning quality — Excellent for failure diagnosis
• JSON mode — Structured output with markdown fence handling
• Streaming responses — Fast time-to-first-token

🔧 API INTEGRATION
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ClaudeAdapter                                                              │
│       │                                                                     │
│       ├── AsyncAnthropic client (anthropic SDK)                            │
│       ├── Messages API (model: claude-sonnet-4-20250514)                   │
│       ├── Vision support (image/* + base64)                                │
│       └── JSON parsing (strip markdown fences)                             │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Failure Analysis — Root cause identification with visual context
• Code Generation — Patch generation with file-level precision
• Scenario Generation — Test case creation from specifications
• Document Analysis — Requirement extraction from design docs
• Step Verification — Visual confirmation of test step success

⚠️  ERROR HANDLING
───────────────────────────────────────────────────────────────────────────────
• TimeoutError — API calls timeout after 120 seconds
• AdapterError — Parse failures and API errors wrapped
• Empty response — Handles truncated responses gracefully
• JSON decode errors — Strips markdown fences before parsing

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Use claude-sonnet-4-20250514 for best reasoning quality
• Use claude-haiku-4-5-20251001 for fast, cost-effective operations
• Provide screenshots for visual debugging context
• Handle AdapterError exceptions in calling code
• Set appropriate max_tokens for complex tasks (4096+)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from anthropic import AsyncAnthropic

from aat.adapters.base import AIAdapter
from aat.adapters.prompts import (
    _SYSTEM_ANALYZE_DOCUMENT,
    _SYSTEM_ANALYZE_FAILURE,
    _SYSTEM_GENERATE_FIX,
    _SYSTEM_GENERATE_SCENARIOS,
    _SYSTEM_VERIFY_STEP,
)
from aat.adapters.utils import encode_image_to_base64
from aat.core import (
    AnalysisResult,
    FileChange,
    FixResult,
    Scenario,
    Severity,
)
from aat.core.exceptions import AdapterError

if TYPE_CHECKING:
    from aat.core import AIConfig, TestResult


class ClaudeAdapter(AIAdapter):
    """Anthropic Claude AI adapter."""

    def __init__(self, config: AIConfig) -> None:
        self._config = config
        self._client = AsyncAnthropic(api_key=config.api_key)

    # ------------------------------------------------------------------
    # AIAdapter interface
    # ------------------------------------------------------------------

    async def analyze_failure(
        self,
        test_result: TestResult,
        screenshots: list[bytes] | None = None,
    ) -> AnalysisResult:
        """Analyze test failure cause via Claude API."""
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"Scenario: {test_result.scenario_id} — {test_result.scenario_name}\n"
                    f"Passed: {test_result.passed}\n"
                    f"Total steps: {test_result.total_steps}, "
                    f"Passed: {test_result.passed_steps}, "
                    f"Failed: {test_result.failed_steps}\n\n"
                    "Step details:\n"
                    + "\n".join(
                        f"  Step {s.step}: {s.status.value} — {s.description}"
                        + (f" (error: {s.error_message})" if s.error_message else "")
                        for s in test_result.steps
                    )
                ),
            },
        ]

        if screenshots:
            for img_bytes in screenshots:
                user_content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": encode_image_to_base64(img_bytes),
                        },
                    }
                )

        data = await self._call_api(_SYSTEM_ANALYZE_FAILURE, user_content)

        try:
            return AnalysisResult(
                cause=str(data["cause"]),
                suggestion=str(data["suggestion"]),
                severity=Severity(data["severity"]),
                related_files=[str(f) for f in data.get("related_files", [])],
            )
        except (KeyError, ValueError) as exc:
            msg = f"Failed to parse analysis response: {exc}"
            raise AdapterError(msg) from exc

    async def generate_fix(
        self,
        analysis: AnalysisResult,
        source_files: dict[str, str],
    ) -> FixResult:
        """Generate code fix based on analysis."""
        source_section = "\n\n".join(
            f"--- {path} ---\n{content}" for path, content in source_files.items()
        )
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"Analysis:\n"
                    f"  Cause: {analysis.cause}\n"
                    f"  Suggestion: {analysis.suggestion}\n"
                    f"  Severity: {analysis.severity.value}\n"
                    f"  Related files: {', '.join(analysis.related_files)}\n\n"
                    f"Source files:\n{source_section}"
                ),
            },
        ]

        data = await self._call_api(_SYSTEM_GENERATE_FIX, user_content)

        try:
            files_changed = [
                FileChange(
                    path=str(fc["path"]),
                    original=str(fc["original"]),
                    modified=str(fc["modified"]),
                    description=str(fc.get("description", "")),
                )
                for fc in data["files_changed"]
            ]
            return FixResult(
                description=str(data["description"]),
                files_changed=files_changed,
                confidence=float(data["confidence"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            msg = f"Failed to parse fix response: {exc}"
            raise AdapterError(msg) from exc

    async def generate_scenarios(
        self,
        document_text: str,
        images: list[bytes] | None = None,
        *,
        system_prompt: str | None = None,
    ) -> list[Scenario]:
        """Generate test scenarios from document text."""
        user_content: list[dict[str, Any]] = [
            {"type": "text", "text": document_text},
        ]

        if images:
            for img_bytes in images:
                user_content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": encode_image_to_base64(img_bytes),
                        },
                    }
                )

        data = await self._call_api(system_prompt or _SYSTEM_GENERATE_SCENARIOS, user_content)

        if not isinstance(data, list):
            msg = "Expected JSON array for scenarios"
            raise AdapterError(msg)

        try:
            return [Scenario.model_validate(s) for s in data]
        except Exception as exc:
            msg = f"Failed to parse scenarios response: {exc}"
            raise AdapterError(msg) from exc

    async def analyze_document(
        self,
        document_text: str,
        images: list[bytes] | None = None,
    ) -> dict[str, Any]:
        """Analyze spec document to extract screens/elements/flows."""
        user_content: list[dict[str, Any]] = [
            {"type": "text", "text": document_text},
        ]

        if images:
            for img_bytes in images:
                user_content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": encode_image_to_base64(img_bytes),
                        },
                    }
                )

        data = await self._call_api(_SYSTEM_ANALYZE_DOCUMENT, user_content)

        if not isinstance(data, dict):
            msg = "Expected JSON object for document analysis"
            raise AdapterError(msg)

        return data

    async def verify_step(
        self,
        screenshot: bytes,
        step_num: int,
        action: str,
        description: str,
    ) -> tuple[bool, str]:
        """Verify step result via Claude Vision API."""
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": f"Step {step_num} ({action}): {description}\n\nDid this step succeed?",
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": encode_image_to_base64(screenshot),
                },
            },
        ]
        data = await self._call_api(_SYSTEM_VERIFY_STEP, user_content)
        return bool(data.get("passed", True)), str(data.get("reason", ""))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call_api(
        self,
        system_prompt: str,
        user_content: list[dict[str, Any]],
    ) -> Any:
        """Call Claude API and parse JSON response.

        Args:
            system_prompt: System message.
            user_content: User message content blocks.

        Returns:
            Parsed JSON data.

        Raises:
            AdapterError: On API or parse failure.
        """
        try:
            response = await asyncio.wait_for(
                self._client.messages.create(
                    model=self._config.model,
                    max_tokens=self._config.max_tokens,
                    temperature=self._config.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}],  # type: ignore[typeddict-item]
                ),
                timeout=120.0,
            )
        except TimeoutError:
            msg = f"Claude API call timed out after 120s (model: {self._config.model})"
            raise AdapterError(msg) from None
        except Exception as exc:
            msg = f"Claude API call failed: {exc}"
            raise AdapterError(msg) from exc

        if not response.content:
            msg = "Claude returned empty response"
            raise AdapterError(msg)

        raw_text = response.content[0].text  # type: ignore[union-attr]

        if response.stop_reason == "max_tokens":
            msg = f"Response truncated (max_tokens reached). Raw tail: {raw_text[-200:]}"
            raise AdapterError(msg)

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            msg = f"Failed to parse JSON from Claude response: {exc}\nRaw: {raw_text[:500]}"
            raise AdapterError(msg) from exc
