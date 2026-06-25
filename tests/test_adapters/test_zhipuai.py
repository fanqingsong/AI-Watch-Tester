"""Tests for ZhipuAIAdapter.

Focus: robust JSON parsing — GLM models often wrap JSON in markdown fences or
return YAML despite the "raw JSON" instruction.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aat.adapters.zhipuai import ZhipuAIAdapter
from aat.core import (
    ActionType,
    AIConfig,
    AnalysisResult,
    Severity,
    StepResult,
    StepStatus,
    TestResult,
)
from aat.core.exceptions import AdapterError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config() -> AIConfig:
    return AIConfig(
        provider="zhipuai",
        api_key="test-key-123",
        model="glm-4.7",
        max_tokens=4000,
        temperature=0.3,
    )


def _make_test_result() -> TestResult:
    return TestResult(
        scenario_id="SC-001",
        scenario_name="Chat test",
        passed=False,
        steps=[
            StepResult(
                step=1,
                action=ActionType.FIND_AND_CLICK,
                status=StepStatus.FAILED,
                description="Click send button",
                error_message="Element not found",
                elapsed_ms=5000.0,
            ),
        ],
        total_steps=1,
        passed_steps=0,
        failed_steps=1,
        duration_ms=5000.0,
    )


def _make_analysis() -> AnalysisResult:
    return AnalysisResult(
        cause="Selector changed",
        suggestion="Update selector",
        severity=Severity.CRITICAL,
        related_files=["src/chat.py"],
    )


def _mock_response(content: str) -> MagicMock:
    """Create a mock ChatCompletion response with the given raw content."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _mock_json(data: Any, fenced: bool = False) -> MagicMock:
    raw = json.dumps(data)
    if fenced:
        raw = f"```json\n{raw}\n```"
    return _mock_response(raw)


@pytest.fixture
def adapter() -> ZhipuAIAdapter:
    config = _make_config()
    with patch("aat.adapters.zhipuai.AsyncOpenAI"):
        return ZhipuAIAdapter(config)


# ---------------------------------------------------------------------------
# Tests: generate_fix (the reported crash site)
# ---------------------------------------------------------------------------


_FIX_DATA = {
    "description": "Update selector",
    "files_changed": [
        {
            "path": "src/chat.py",
            "original": "old",
            "modified": "new",
            "description": "fixed",
        }
    ],
    "confidence": 0.9,
}


@pytest.mark.asyncio
async def test_generate_fix_plain_json(adapter: ZhipuAIAdapter) -> None:
    """generate_fix parses a clean JSON response."""
    adapter.client.chat.completions.create = AsyncMock(
        return_value=_mock_json(_FIX_DATA),
    )
    result = await adapter.generate_fix(_make_analysis(), {"src/chat.py": "old"})

    assert result.description == "Update selector"
    assert len(result.files_changed) == 1
    assert result.files_changed[0].path == "src/chat.py"
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_generate_fix_strips_markdown_fences(adapter: ZhipuAIAdapter) -> None:
    """Regression: GLM wraps JSON in ```json ... ```. Must not raise char-0 error."""
    adapter.client.chat.completions.create = AsyncMock(
        return_value=_mock_json(_FIX_DATA, fenced=True),
    )
    result = await adapter.generate_fix(_make_analysis(), {"src/chat.py": "old"})

    assert result.description == "Update selector"
    assert result.files_changed[0].modified == "new"


@pytest.mark.asyncio
async def test_generate_fix_yaml_fallback(adapter: ZhipuAIAdapter) -> None:
    """generate_fix falls back to YAML when JSON parsing fails."""
    yaml_text = "description: Update selector\nfiles_changed: []\nconfidence: 0.5\n"
    adapter.client.chat.completions.create = AsyncMock(
        return_value=_mock_response(yaml_text),
    )
    result = await adapter.generate_fix(_make_analysis(), {})

    assert result.description == "Update selector"
    assert result.files_changed == []


@pytest.mark.asyncio
async def test_generate_fix_empty_response(adapter: ZhipuAIAdapter) -> None:
    """generate_fix raises a clear error on empty response (not char-0 JSON)."""
    adapter.client.chat.completions.create = AsyncMock(
        return_value=_mock_response(""),
    )
    with pytest.raises(AdapterError, match="Empty response from ZhipuAI"):
        await adapter.generate_fix(_make_analysis(), {})


@pytest.mark.asyncio
async def test_generate_fix_unparseable(adapter: ZhipuAIAdapter) -> None:
    """generate_fix raises AdapterError when response is neither JSON nor YAML."""
    adapter.client.chat.completions.create = AsyncMock(
        return_value=_mock_response("sorry, I cannot help with that"),
    )
    with pytest.raises(AdapterError, match="Failed to parse ZhipuAI response"):
        await adapter.generate_fix(_make_analysis(), {})


# ---------------------------------------------------------------------------
# Tests: analyze_failure
# ---------------------------------------------------------------------------


_ANALYSIS_DATA = {
    "cause": "Selector changed",
    "suggestion": "Use .btn-send",
    "severity": "critical",
    "related_files": ["src/chat.py"],
}


@pytest.mark.asyncio
async def test_analyze_failure_plain_json(adapter: ZhipuAIAdapter) -> None:
    adapter.client.chat.completions.create = AsyncMock(
        return_value=_mock_json(_ANALYSIS_DATA),
    )
    result = await adapter.analyze_failure(_make_test_result())

    assert result.cause == "Selector changed"
    assert result.severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_analyze_failure_strips_markdown_fences(adapter: ZhipuAIAdapter) -> None:
    """Regression: analyze_failure must strip fences too."""
    adapter.client.chat.completions.create = AsyncMock(
        return_value=_mock_json(_ANALYSIS_DATA, fenced=True),
    )
    result = await adapter.analyze_failure(_make_test_result())

    assert result.cause == "Selector changed"


@pytest.mark.asyncio
async def test_analyze_failure_empty_response(adapter: ZhipuAIAdapter) -> None:
    adapter.client.chat.completions.create = AsyncMock(
        return_value=_mock_response("   "),
    )
    with pytest.raises(AdapterError, match="Empty response from ZhipuAI"):
        await adapter.analyze_failure(_make_test_result())


# ---------------------------------------------------------------------------
# Tests: analyze_document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_document_strips_fences(adapter: ZhipuAIAdapter) -> None:
    data = {"screens": ["Chat"], "elements": ["input"], "flows": ["send"]}
    adapter.client.chat.completions.create = AsyncMock(
        return_value=_mock_json(data, fenced=True),
    )
    result = await adapter.analyze_document("Spec text")

    assert result["screens"] == ["Chat"]


# ---------------------------------------------------------------------------
# Tests: registry
# ---------------------------------------------------------------------------


def test_adapter_registry() -> None:
    from aat.adapters import ADAPTER_REGISTRY

    assert "zhipuai" in ADAPTER_REGISTRY
    assert ADAPTER_REGISTRY["zhipuai"] is ZhipuAIAdapter
