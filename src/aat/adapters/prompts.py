"""Shared prompt templates for AI adapters.

This module contains common prompt templates used across multiple AI adapters
(Claude, OpenAI, Ollama, etc.) to avoid duplication.
"""

# ---------------------------------------------------------------------------
# Core prompt templates (shared across all adapters)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Core prompt templates (shared across all adapters)
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
You are an expert QA engineer. Given a specification document, generate test \
scenarios as a JSON array.

## URL EXTRACTION INSTRUCTIONS
CRITICAL: You MUST extract the base URL from the specification document:
1. Look for sections like "## 测试页面", "Test Page", "URL:", "- URL:"
2. Extract the URL from these sections
3. Use this EXACT URL for all navigate actions
4. Do NOT use placeholders like {{url}} or similar

Example:
If the specification says:
  ## 测试页面
  - URL: http://localhost:5173/

Then your navigate action should be:
  {"step": 1, "action": "navigate", "value": "http://localhost:5173/", "description": "Go to login"}

Each scenario must follow this EXACT format:
{"id": "SC-001", "name": "Short name", "description": "What this tests", \
"tags": ["tag1"], "steps": [...], "expected_result": []}

"expected_result" must be an array of objects (NOT strings), each with:
  {"type": "text_visible", "value": "expected text"}
Valid types: "text_visible", "text_equals", "url_contains".
Leave as empty array [] if no specific assertion is needed.

Each step MUST have "step" (integer from 1) and "description" (non-empty).

VALID ACTIONS (use ONLY these):
- "navigate" — requires "value" with FULL URL. Example:
  {"step": 1, "action": "navigate", "value": "http://localhost:5173/", "description": "Go to login"}
- "find_and_click" — requires "target" with "text". Example:
  {"step": 2, "action": "find_and_click", "target": {"text": "Login"}, \
"description": "Click login", "humanize": true}
- "find_and_type" — requires "target" with "text" AND "value". Example:
  {"step": 3, "action": "find_and_type", "target": {"text": "Email"}, \
"value": "user@test.com", "description": "Enter email", "humanize": true}
- "type_text" — types into focused field. Example:
  {"step": 4, "action": "type_text", "value": "hello", "description": "Type text"}
- "press_key" — press a key. Example:
  {"step": 5, "action": "press_key", "value": "Enter", "description": "Press enter"}
- "assert" — requires "assert_type" and "expected". Example:
  {"step": 6, "action": "assert", "assert_type": "text_visible", \
"expected": [{"type": "text_visible", "value": "Welcome"}], "description": "Verify text"}
- "wait" — milliseconds. Example:
  {"step": 7, "action": "wait", "value": "2000", "description": "Wait 2s"}
- "screenshot" — capture screen. Example:
  {"step": 8, "action": "screenshot", "description": "Capture state"}

BUSINESS FLOW ORDERING:
- Generate scenarios in logical business flow order \
(e.g., sign up BEFORE login, login BEFORE dashboard)
- Add "depends_on" field (array of scenario IDs) when a scenario \
requires another to pass first. Example:
{"id": "SC-002", "depends_on": ["SC-001"], ...}
- SC-001 should have no dependencies. Later scenarios depend on earlier ones.

CRITICAL RULES:
- "click" is INVALID. Use "find_and_click"
- "type" is INVALID. Use "find_and_type"
- target must NOT have "role" or "url" fields. Only "text"
- EXTRACT THE ACTUAL URL FROM THE SPECIFICATION DOCUMENT
- Look for "## 测试页面", "Test Page", "URL:", "- URL:" or similar sections
- Use the COMPLETE URL, not placeholders
- Do NOT include "variables" with hardcoded URLs

PAGE ELEMENTS (when provided):
The document MAY end with a "## PAGE ELEMENTS" section listing the real \
interactive elements detected on the scanned page. When this section is \
present, you MUST use those EXACT labels verbatim as the "text" for \
find_and_click / find_and_type targets — do not paraphrase or invent labels. \
When the section is absent, infer target labels from the specification as usual.

Return ONLY a valid JSON array, no markdown fences."""

_SYSTEM_ANALYZE_DOCUMENT = """\
You are an expert QA engineer. Analyze the following document and extract:
- "screens": list of screen/page descriptions
- "elements": list of UI elements found
- "flows": list of user flows described

Return ONLY valid JSON, no markdown fences."""

# ---------------------------------------------------------------------------
# Claude-specific prompts (only used by ClaudeAdapter)
# ---------------------------------------------------------------------------

_SYSTEM_VERIFY_STEP = """\
You are a QA verification assistant. A browser screenshot was taken AFTER a test step executed.
Determine if the step succeeded based on what you see in the screenshot.
Consider: Did the expected UI change happen? Is the page correct? Are there error messages?
Return ONLY valid JSON: {"passed": true, "reason": "brief one-sentence explanation"}"""

__all__ = [
    "_SYSTEM_ANALYZE_FAILURE",
    "_SYSTEM_GENERATE_FIX",
    "_SYSTEM_GENERATE_SCENARIOS",
    "_SYSTEM_ANALYZE_DOCUMENT",
    "_SYSTEM_VERIFY_STEP",
]
