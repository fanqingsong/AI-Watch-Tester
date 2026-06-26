"""
════════════════════════════════════════════════════════════════════════════════
                 📝 AI Prompt Templates Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Shared prompt templates for AI adapters. Contains common system prompts used
across multiple AI providers (Claude, OpenAI, Ollama, etc.) to ensure
consistent behavior and avoid duplication.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.adapters.prompts import _SYSTEM_ANALYZE_FAILURE, _SYSTEM_GENERATE_SCENARIOS

# Use in any AI adapter
messages = [
    {"role": "system", "content": _SYSTEM_ANALYZE_FAILURE},
    {"role": "user", "content": failure_context}
]

response = await client.chat.completions.create(messages=messages)
```

⚙️  AVAILABLE PROMPTS
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Prompt Template            │  Purpose                              │
├────────────────────────────────────────────────────────────────────────────┤
│  _SYSTEM_ANALYZE_FAILURE    │  Diagnose test failure root causes    │
│  _SYSTEM_GENERATE_FIX       │  Generate code patches for fixes       │
│  _SYSTEM_GENERATE_SCENARIOS │  Create test scenarios from specs      │
│  _SYSTEM_ANALYZE_DOCUMENT   │  Extract requirements from documents    │
│  _SYSTEM_VERIFY_STEP        │  Visual step verification (Claude)      │
│  _SYSTEM_EXTRACT_PARAMS     │  Extract test parameters from text      │
└────────────────────────────────────────────────────────────────────────────┘

📦 PROMPT CATEGORIES
───────────────────────────────────────────────────────────────────────────────
Core Templates (used by all adapters):
• _SYSTEM_ANALYZE_FAILURE — Failure diagnosis with cause/suggestion/severity
• _SYSTEM_GENERATE_FIX — Code patch generation with file changes
• _SYSTEM_GENERATE_SCENARIOS — Test scenario creation from specifications
• _SYSTEM_ANALYZE_DOCUMENT — Requirement extraction from design documents

Provider-Specific Templates:
• _SYSTEM_VERIFY_STEP — Claude-specific visual step verification
• _SYSTEM_EXTRACT_PARAMS — Parameter extraction from natural language

🔧 PROMPT DESIGN PRINCIPLES
───────────────────────────────────────────────────────────────────────────────
• JSON Output — All prompts request structured JSON responses
• No Markdown Fences — Explicitly request raw JSON (no ```json ... ```)
• Clear Field Specifications — Define exact JSON structure required
• Error Handling — Include instructions for handling edge cases
• Context Awareness — Provide relevant context for each task

📋 SCENARIO GENERATION FEATURES
───────────────────────────────────────────────────────────────────────────────
The _SYSTEM_GENERATE_SCENARIOS prompt includes:
• URL Extraction — Instructions to extract base URLs from specifications
• Action Validation — Valid action names and required fields
• Business Flow Ordering — Logical scenario sequencing
• Dependency Management — depends_on field for prerequisite scenarios
• Page Element Integration — Using scan data for reliable selectors
• Expected Result Format — Structured assertions with type/value pairs

⚠️  PROMPT MAINTENANCE
───────────────────────────────────────────────────────────────────────────────
• Version Control — Changes affect all adapters simultaneously
• Testing Required — Test with multiple providers after modifications
• Backward Compatibility — Consider impact on existing scenarios
• Provider Differences — Some providers may need slight variations

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
• Keep prompts language-agnostic — Avoid provider-specific terminology
• Specify JSON structure clearly — Define exact field names and types
• Include examples — Show expected input/output format
• Request raw JSON — Explicitly forbid markdown fences
• Handle edge cases — Provide instructions for ambiguous situations

🎯 USAGE PATTERN
───────────────────────────────────────────────────────────────────────────────
```python
# Import required prompts
from aat.adapters.prompts import (
    _SYSTEM_ANALYZE_FAILURE,
    _SYSTEM_GENERATE_FIX,
    _SYSTEM_GENERATE_SCENARIOS
)

# Use in adapter methods
messages = [
    {"role": "system", "content": _SYSTEM_ANALYZE_FAILURE},
    {"role": "user", "content": user_context}
]

response = await client.messages.create(messages=messages)
result = json.loads(response.content[0].text)
```

════════════════════════════════════════════════════════════════════════════════
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
  {"step": 1, "action": "navigate",
   "value": "http://localhost:5173/",
   "description": "Go to login"}

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
  {"step": 1, "action": "navigate", "value": "http://localhost:5173/",
   "description": "Go to login"}
- "find_and_click" — requires "target" with element selectors. Example:
  {"step": 2, "action": "find_and_click",
   "target": {"selector": "[ref=e11]", "snapshot_ref": "e11", "text": "Login"},
   "description": "Click login", "humanize": true}
- "find_and_type" — requires "target" with element selectors AND "value". Example:
  {"step": 3, "action": "find_and_type", "value": "user@test.com",
   "target": {"selector": "[ref=e12]", "snapshot_ref": "e12", "text": "Email",
             "role": "textbox"},
   "description": "Enter email", "humanize": true}
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
- For find_and_click and find_and_type, ALWAYS include selector/
  snapshot_ref when available from scan data
- target CAN have these fields: "text", "selector", "snapshot_ref", "role"
- Prefer selector-based targeting over text-only for reliability
- EXTRACT THE ACTUAL URL FROM THE SPECIFICATION DOCUMENT
- Look for "## 测试页面", "Test Page", "URL:", "- URL:" or similar sections
- Use the COMPLETE URL, not placeholders
- Do NOT include "variables" with hardcoded URLs

PAGE ELEMENTS (when provided):
The document MAY end with a "## PAGE ELEMENTS" section listing the real \
interactive elements detected on the scanned page. When this section is \
present, you MUST use those EXACT element selectors for find_and_click / \
find_and_type targets in this priority order:

1. Use BOTH "selector" and "snapshot_ref" when available (most reliable)
2. Use "selector" + "text" when snapshot_ref is not available
3. Use "text" only as fallback (least reliable)

Example from PAGE ELEMENTS section:
  textbox | "Email/Account" | selector=[ref=e11] | snapshot_ref=e11
Should generate:
  {"step": 2, "action": "find_and_type", "value": "admin@example.com",
   "target": {"selector": "[ref=e11]", "snapshot_ref": "e11",
             "text": "Email/Account", "role": "textbox"},
   "value": "admin@example.com", "description": "Enter email"}

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

_SYSTEM_EXTRACT_PARAMS = """\
You are an expert QA engineer. Extract test parameters from a natural language description.

Given a test description and an input field type, extract the appropriate test value.
Consider context, intent, and any explicit or implicit parameter mentions.

Return ONLY a valid JSON object with:
- "value": the extracted test value (string)
- "confidence": float 0.0-1.0 (how confident you are this is correct)
- "reasoning": brief explanation (optional)

Examples:
Description: "test search function of bing, using search words: AI NEWS"
Input type: search
Result: {"value": "AI NEWS", "confidence": 0.95, "reasoning": "explicitly stated search words"}

Description: "login with test@example.com and pass123"
Input type: email
Result: {"value": "test@example.com", "confidence": 0.9, "reasoning": "email found in description"}

Description: "check the signup flow"
Input type: text
Result: {"value": "test user", "confidence": 0.7, "reasoning": "generic test value for signup"}

Return ONLY valid JSON, no markdown fences."""

__all__ = [
    "_SYSTEM_ANALYZE_FAILURE",
    "_SYSTEM_GENERATE_FIX",
    "_SYSTEM_GENERATE_SCENARIOS",
    "_SYSTEM_ANALYZE_DOCUMENT",
    "_SYSTEM_VERIFY_STEP",
    "_SYSTEM_EXTRACT_PARAMS",
]
