"""
════════════════════════════════════════════════════════════════════════════════
                   🤖 OpenAI Adapter Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
OpenAI GPT API integration for AI-powered test failure analysis, code fix
generation, and test scenario creation. Features Structured Outputs for
guaranteed JSON schema compliance and vision capabilities for screenshot analysis.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.adapters.openai_adapter import OpenAIAdapter
from aat.core import AIConfig

config = AIConfig(
    provider="openai",
    api_key="sk-...",
    model="gpt-4o"
)

adapter = OpenAIAdapter(config)

# Analyze test failure with screenshot
analysis = await adapter.analyze_failure(
    test_result=result,
    screenshots=[screenshot_bytes]
)

# Generate code fix
fix = await adapter.generate_fix(analysis, source_files)

# Generate scenarios with Structured Outputs
scenarios = await adapter.generate_scenarios(document_text, images)
```

⚙️  CAPABILITIES
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Method              │  Vision  │  Structured  │  Purpose                  │
├────────────────────────────────────────────────────────────────────────────┤
│  analyze_failure()   │    ✅     │      ❌      │  Diagnose with screenshots │
│  generate_fix()      │    ❌     │      ❌      │  Generate code patches     │
│  generate_scenarios()│    ✅     │      ✅      │  Create scenarios (SO)      │
│  analyze_document()  │    ✅     │      ❌      │  Extract from docs         │
└────────────────────────────────────────────────────────────────────────────┘

🧠 OPENAI API FEATURES
───────────────────────────────────────────────────────────────────────────────
• Structured Outputs — Guaranteed JSON schema compliance
• Vision API — Screenshot analysis for visual debugging
• GPT-4o — Multimodal model with excellent reasoning
• GPT-4o-mini — Faster, cheaper option for simple tasks
• JSON Mode — Fallback to json_object when schema not provided

🔧 API INTEGRATION
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  OpenAIAdapter                                                              │
│       │                                                                     │
│       ├── AsyncOpenAI client (openai SDK)                                   │
│       ├── Chat Completions API                                              │
│       ├── Structured Outputs (json_schema)                                  │
│       ├── Vision support (image_url + base64)                               │
│       └── YAML fallback parsing                                             │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

📦 STRUCTURED OUTPUTS
───────────────────────────────────────────────────────────────────────────────
OpenAI's Structured Outputs feature enforces JSON schema compliance at the
model level, eliminating format errors:
• Guaranteed schema match — No missing fields or invalid values
• Semantic validation only — Wrong selector/text values still possible
• Used for scenario generation — Ensures valid action names, field types
• Fallback to json_object — When schema not provided

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• Failure Analysis — Root cause identification with visual context
• Code Generation — Patch generation with file-level precision
• Scenario Generation — Test case creation with Structured Outputs
• Document Analysis — Requirement extraction from design docs
• Visual Verification — Screenshot-based step validation

⚠️  ERROR HANDLING
───────────────────────────────────────────────────────────────────────────────
• TimeoutError — API calls timeout after 120 seconds
• AdapterError — Parse failures and API errors wrapped
• Empty response — Handles truncated responses gracefully
• JSON decode errors — Strips markdown fences, tries YAML fallback
• Length finish reason — Warns on max_tokens truncation

💡 MODEL RECOMMENDATIONS
───────────────────────────────────────────────────────────────────────────────
• gpt-4o — Best for complex reasoning and visual tasks
• gpt-4o-mini — Faster, cheaper for simple operations
• gpt-4-turbo — Legacy model, consider gpt-4o instead

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Production workloads requiring high quality
✅ Visual debugging with screenshot analysis
✅ Scenario generation requiring guaranteed schema compliance
✅ Complex failure diagnosis requiring strong reasoning
❌ Cost-sensitive operations (consider DeepSeek/Ollama)
❌ Simple text-only tasks (consider cheaper models)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured Output JSON Schema — scenario generation
# ---------------------------------------------------------------------------
# OpenAI Structured Outputs (json_schema mode) enforces schema compliance
# at the model level, eliminating format errors like missing assert_type,
# invalid action names, etc.  Semantic errors (wrong selector, wrong assert
# value) are NOT prevented by this — the post-processing pipeline handles
# those.

_SCENARIO_JSON_SCHEMA: dict[str, Any] = {
    "name": "test_scenarios",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "scenarios": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "step": {"type": "integer"},
                                    "action": {
                                        "type": "string",
                                        "enum": [
                                            "navigate",
                                            "find_and_click",
                                            "find_and_type",
                                            "assert",
                                            "wait",
                                            "scroll",
                                            "type_text",
                                            "press_key",
                                            "screenshot",
                                        ],
                                    },
                                    "target": {
                                        "anyOf": [
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "selector": {
                                                        "anyOf": [
                                                            {"type": "string"},
                                                            {"type": "null"},
                                                        ],
                                                    },
                                                    "text": {
                                                        "anyOf": [
                                                            {"type": "string"},
                                                            {"type": "null"},
                                                        ],
                                                    },
                                                },
                                                "required": ["selector", "text"],
                                                "additionalProperties": False,
                                            },
                                            {"type": "null"},
                                        ],
                                    },
                                    "value": {
                                        "anyOf": [
                                            {"type": "string"},
                                            {"type": "null"},
                                        ],
                                    },
                                    "assert_type": {
                                        "anyOf": [
                                            {
                                                "type": "string",
                                                "enum": [
                                                    "text_visible",
                                                    "text_equals",
                                                    "image_visible",
                                                    "url_contains",
                                                    "url_not_contains",
                                                    "screenshot_match",
                                                ],
                                            },
                                            {"type": "null"},
                                        ],
                                    },
                                    "case_insensitive": {
                                        "anyOf": [
                                            {"type": "boolean"},
                                            {"type": "null"},
                                        ],
                                    },
                                    "description": {"type": "string"},
                                    "humanize": {
                                        "anyOf": [
                                            {"type": "boolean"},
                                            {"type": "null"},
                                        ],
                                    },
                                    "expected": {
                                        "anyOf": [
                                            {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "type": {"type": "string"},
                                                        "value": {"type": "string"},
                                                    },
                                                    "required": ["type", "value"],
                                                    "additionalProperties": False,
                                                },
                                            },
                                            {"type": "null"},
                                        ],
                                    },
                                },
                                "required": [
                                    "step",
                                    "action",
                                    "description",
                                    "target",
                                    "value",
                                    "assert_type",
                                    "case_insensitive",
                                    "humanize",
                                    "expected",
                                ],
                                "additionalProperties": False,
                            },
                        },
                        "tags": {
                            "anyOf": [
                                {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                {"type": "null"},
                            ],
                        },
                        "depends_on": {
                            "anyOf": [
                                {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": (
                                        "Scenario IDs that must pass before this one"
                                        " (e.g. ['SC-001'])"
                                    ),
                                },
                                {"type": "null"},
                            ],
                        },
                    },
                    "required": [
                        "id",
                        "name",
                        "description",
                        "steps",
                        "tags",
                        "depends_on",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["scenarios"],
        "additionalProperties": False,
    },
}


class OpenAIAdapter(AIAdapter):
    """OpenAI GPT AI adapter.

    Uses the OpenAI API with vision support for image analysis.
    """

    def __init__(self, config: AIConfig) -> None:
        self._config = config
        self._client = AsyncOpenAI(api_key=config.api_key)

    # ------------------------------------------------------------------
    # AIAdapter interface
    # ------------------------------------------------------------------

    async def analyze_failure(
        self,
        test_result: TestResult,
        screenshots: list[bytes] | None = None,
    ) -> AnalysisResult:
        """Analyze test failure cause via OpenAI API."""
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"Scenario: {test_result.scenario_id}"
                    f" — {test_result.scenario_name}\n"
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
                        "type": "image_url",
                        "image_url": {
                            "url": (f"data:image/png;base64,{encode_image_to_base64(img_bytes)}"),
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
                        "type": "image_url",
                        "image_url": {
                            "url": (f"data:image/png;base64,{encode_image_to_base64(img_bytes)}"),
                        },
                    }
                )

        data = await self._call_api(
            system_prompt or _SYSTEM_GENERATE_SCENARIOS,
            user_content,
            json_schema=_SCENARIO_JSON_SCHEMA,
        )

        # Unwrap {"scenarios": [...]} wrapper (json_object mode returns objects)
        if isinstance(data, dict) and "scenarios" in data:
            data = data["scenarios"]

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
                        "type": "image_url",
                        "image_url": {
                            "url": (f"data:image/png;base64,{encode_image_to_base64(img_bytes)}"),
                        },
                    }
                )

        data = await self._call_api(_SYSTEM_ANALYZE_DOCUMENT, user_content)

        if not isinstance(data, dict):
            msg = "Expected JSON object for document analysis"
            raise AdapterError(msg)

        return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call_api(
        self,
        system_prompt: str,
        user_content: list[dict[str, Any]],
        *,
        json_schema: dict[str, Any] | None = None,
    ) -> Any:
        """Call OpenAI Chat Completions API and parse JSON response.

        Args:
            system_prompt: System message.
            user_content: User message content blocks.
            json_schema: Optional JSON schema for Structured Outputs mode.

        Returns:
            Parsed JSON data.

        Raises:
            AdapterError: On API or parse failure.
        """
        if json_schema is not None:
            response_fmt: dict[str, Any] = {
                "type": "json_schema",
                "json_schema": json_schema,
            }
        else:
            response_fmt = {"type": "json_object"}

        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(  # type: ignore[call-overload]
                    model=self._config.model,
                    max_tokens=self._config.max_tokens,
                    temperature=self._config.temperature,
                    response_format=response_fmt,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                ),
                timeout=120.0,  # 2 minute timeout
            )
        except TimeoutError:
            msg = f"OpenAI API call timed out after 120s (model: {self._config.model})"
            raise AdapterError(msg) from None
        except Exception as exc:
            msg = f"OpenAI API call failed: {exc}"
            raise AdapterError(msg) from exc

        if not response.choices:
            msg = "OpenAI returned empty response (no choices)"
            raise AdapterError(msg)

        choice = response.choices[0]
        raw_text = choice.message.content or ""

        if choice.finish_reason == "length":
            msg = f"Response truncated (max_tokens reached). Raw tail: {raw_text[-200:]}"
            raise AdapterError(msg)

        if not raw_text:
            msg = "Empty response from OpenAI"
            raise AdapterError(msg)

        # Strip markdown fences if the model wraps JSON in ```json ... ```
        cleaned = AIAdapter._strip_markdown_fences(raw_text)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as json_err:
            # Fallback: try YAML parsing (some models return YAML despite JSON instructions)
            try:
                import yaml

                result = yaml.safe_load(cleaned)
                if isinstance(result, (dict, list)):
                    logger.warning(
                        "OpenAI returned YAML instead of JSON, parsed via YAML fallback"
                    )
                    return result
            except Exception:
                pass
            msg = f"Failed to parse JSON from OpenAI response: {json_err}\nRaw: {raw_text[:500]}"
            raise AdapterError(msg) from json_err
