"""AI Fix Guide generation — analyze test failures and suggest code fixes."""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

FIX_GUIDE_PROMPT = """\
You are an expert QA engineer analyzing a failed E2E test.

## Failed Scenario
- Scenario: {scenario_name} ({scenario_id})
- Target URL: {target_url}

## Failed Steps
{failed_steps}

## Task
Analyze the failure and suggest concrete code fixes. For each file that needs changes:
1. Identify the likely source file
2. Show the original code snippet
3. Show the suggested fix
4. Explain why this change fixes the issue

Respond ONLY with valid JSON (no markdown fences) in this format:
{{
  "summary": "Brief explanation of what went wrong and how to fix it",
  "files": [
    {{
      "path": "src/example.tsx",
      "action": "modify",
      "original": "original code snippet",
      "suggested": "fixed code snippet",
      "explanation": "why this change is needed"
    }}
  ]
}}

If the failure is due to a test configuration issue (not a code bug), still provide
the JSON with a helpful summary and an empty files array.
"""


def _format_failed_steps(scenario: dict) -> str:
    """Format failed steps for the AI prompt."""
    lines = []
    for step in scenario.get("steps", []):
        status = step.get("status", "")
        if status in ("failed", "error"):
            lines.append(
                f"- Step {step.get('step', '?')}: {step.get('action', '?')} "
                f"— {step.get('description', '')}\n"
                f"  Target: {step.get('target', '')}\n"
                f"  Error: {step.get('error', 'unknown')}"
            )
    return "\n".join(lines) if lines else "No specific step failure details available."


def _extract_json(text: str) -> dict | None:
    """Extract JSON from AI response, handling markdown fences."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try removing markdown fences
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    return None


async def generate_fix_guide(
    test_result: dict,
    scenario_result: dict,
    target_url: str,
    ai_config: object,
) -> dict:
    """Generate a fix guide using AI.

    Args:
        test_result: Full test result_json parsed dict.
        scenario_result: The specific failed scenario dict.
        target_url: The test target URL.
        ai_config: AIConfig object with provider/api_key/model.

    Returns:
        {"summary": ..., "files": [...]} or raises.
    """
    from aat.adapters import ADAPTER_REGISTRY

    adapter_cls = ADAPTER_REGISTRY.get(ai_config.provider)  # type: ignore[attr-defined]
    if adapter_cls is None:
        raise ValueError(f"Unknown AI provider: {ai_config.provider}")  # type: ignore[attr-defined]

    adapter = adapter_cls(ai_config)

    prompt = FIX_GUIDE_PROMPT.format(
        scenario_name=scenario_result.get("scenario_name", "Unknown"),
        scenario_id=scenario_result.get("scenario_id", "unknown"),
        target_url=target_url,
        failed_steps=_format_failed_steps(scenario_result),
    )

    # Use adapter's raw generation if available, otherwise fall back
    try:
        response_text = await adapter.generate_raw(prompt)
    except AttributeError:
        # Fallback: use generate method with a minimal context
        response_text = await adapter.generate(
            system_prompt="You are a code fix assistant. Respond only with JSON.",
            user_prompt=prompt,
        )

    if not response_text:
        return {"summary": "AI returned no response.", "files": []}

    result = _extract_json(response_text)
    if result is None:
        logger.warning("Failed to parse AI fix guide response: %s", response_text[:200])
        return {
            "summary": response_text[:500],
            "files": [],
        }

    # Validate structure
    if "summary" not in result:
        result["summary"] = "AI analysis complete."
    if "files" not in result:
        result["files"] = []

    return result
