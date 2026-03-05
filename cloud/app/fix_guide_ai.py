"""AI Fix Guide generation — analyze test failures and suggest code fixes."""

from __future__ import annotations

import base64
import json
import logging
import re
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Noise directories/extensions to skip when building file tree
_TREE_SKIP_DIRS = {"node_modules", ".next", "dist", "__pycache__", ".git", ".venv", "venv"}
_TREE_SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm",
}
_CODE_EXTS = {".tsx", ".ts", ".js", ".jsx", ".py", ".vue", ".svelte", ".html", ".css"}
_CONFIG_FILES = {"package.json", "pyproject.toml"}
_MAX_TREE_PATHS = 300
_MAX_FILE_SIZE = 100_000  # 100KB
_MAX_FILE_CONTENT_LEN = 2000
_MAX_SOURCE_CONTEXT_LEN = 8000
_MAX_RELEVANT_FILES = 5

FIX_GUIDE_PROMPT = """\
You are an expert QA engineer analyzing a failed E2E test.

## Failed Scenario
- Scenario: {scenario_name} ({scenario_id})
- Target URL: {target_url}

## Failed Steps
{failed_steps}
{source_context}
## Task
Analyze the failure and suggest concrete code fixes.
Use EXACT file paths from the project structure above when available.
For each file that needs changes:
1. Identify the source file (use exact paths from the project)
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

IMPORTANT: Write ALL text values (summary, explanation) in {response_language}.
Code snippets (original, suggested, path) remain in their original language.
"""

# Map locale code → language name for the prompt
_LOCALE_TO_LANG: dict[str, str] = {
    "ko": "Korean",
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
}


# ---------------------------------------------------------------------------
# Source code fetching helpers
# ---------------------------------------------------------------------------


async def _fetch_file_tree(
    pat: str, owner: str, repo: str, branch: str,
) -> list[str]:
    """Fetch repository file tree via GitHub API (recursive)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params={"recursive": "1"}, headers=headers)
    if resp.status_code != 200:
        logger.debug("File tree fetch failed: %d", resp.status_code)
        return []

    data = resp.json()
    if data.get("truncated"):
        logger.warning("File tree truncated for %s/%s", owner, repo)

    paths: list[str] = []
    for item in data.get("tree", []):
        if item.get("type") != "blob":
            continue
        path = item["path"]
        # Skip noise directories
        parts = path.split("/")
        if any(p in _TREE_SKIP_DIRS for p in parts):
            continue
        # Skip binary/asset extensions
        ext = ""
        if "." in parts[-1]:
            ext = "." + parts[-1].rsplit(".", 1)[1].lower()
        if ext in _TREE_SKIP_EXTS:
            continue
        paths.append(path)
        if len(paths) >= _MAX_TREE_PATHS:
            break
    return paths


async def _fetch_file_content(
    pat: str, owner: str, repo: str, path: str, branch: str,
) -> str | None:
    """Fetch a single file's content from GitHub (base64 decoded)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params={"ref": branch}, headers=headers)
    if resp.status_code != 200:
        logger.debug("File content fetch failed for %s: %d", path, resp.status_code)
        return None

    data = resp.json()
    size = data.get("size", 0)
    if size > _MAX_FILE_SIZE:
        return None

    content_b64 = data.get("content", "")
    try:
        return base64.b64decode(content_b64).decode("utf-8", errors="replace")
    except Exception:
        return None


def _identify_relevant_files(
    file_tree: list[str],
    scenario_result: dict,
    target_url: str,
) -> list[str]:
    """Pick the most relevant source files from the tree."""
    relevant: list[str] = []
    seen: set[str] = set()

    # 1. Extract file paths mentioned in error messages
    error_texts: list[str] = []
    for step in scenario_result.get("steps", []):
        if step.get("status") in ("failed", "error"):
            err = step.get("error", "")
            if err:
                error_texts.append(err)

    code_ext_pattern = r"[\w/.-]+(?:" + "|".join(
        re.escape(e) for e in _CODE_EXTS
    ) + r")"
    for text in error_texts:
        for match in re.findall(code_ext_pattern, text):
            # Find matching path in tree
            for tree_path in file_tree:
                if tree_path.endswith(match) or match in tree_path:
                    if tree_path not in seen:
                        relevant.append(tree_path)
                        seen.add(tree_path)
                    break

    # 2. URL path mapping — match URL segments to code files
    parsed = urlparse(target_url)
    url_path = parsed.path.strip("/")
    if url_path:
        segments = url_path.split("/")
        for seg in segments:
            if not seg:
                continue
            for tree_path in file_tree:
                if tree_path in seen:
                    continue
                ext = ""
                fname = tree_path.rsplit("/", 1)[-1]
                if "." in fname:
                    ext = "." + fname.rsplit(".", 1)[1].lower()
                if ext not in _CODE_EXTS:
                    continue
                if seg.lower() in tree_path.lower():
                    relevant.append(tree_path)
                    seen.add(tree_path)
                    if len(relevant) >= _MAX_RELEVANT_FILES:
                        break
            if len(relevant) >= _MAX_RELEVANT_FILES:
                break

    # 3. Config files
    if len(relevant) < _MAX_RELEVANT_FILES:
        for tree_path in file_tree:
            fname = tree_path.rsplit("/", 1)[-1]
            if fname in _CONFIG_FILES and tree_path not in seen:
                relevant.append(tree_path)
                seen.add(tree_path)
                if len(relevant) >= _MAX_RELEVANT_FILES:
                    break

    return relevant[:_MAX_RELEVANT_FILES]


async def _build_source_context(
    pat: str,
    owner: str,
    repo: str,
    branch: str,
    file_tree: list[str],
    relevant_files: list[str],
) -> str:
    """Build a source context string with project structure + file contents."""
    parts: list[str] = []
    total_len = 0

    # Render partial file tree (3 depth levels, ~1000 chars)
    tree_lines: list[str] = []
    for path in file_tree:
        depth = path.count("/")
        if depth <= 2:
            tree_lines.append(path)
    tree_str = "\n".join(tree_lines[:80])
    if tree_str:
        section = f"\n## Project Structure (partial)\n```\n{tree_str}\n```\n"
        parts.append(section)
        total_len += len(section)

    # Fetch and render relevant file contents
    for fpath in relevant_files:
        if total_len >= _MAX_SOURCE_CONTEXT_LEN:
            break
        content = await _fetch_file_content(pat, owner, repo, fpath, branch)
        if content is None:
            continue
        truncated = content[:_MAX_FILE_CONTENT_LEN]
        if len(content) > _MAX_FILE_CONTENT_LEN:
            truncated += "\n... (truncated)"
        section = f"\n## Source: {fpath}\n```\n{truncated}\n```\n"
        if total_len + len(section) > _MAX_SOURCE_CONTEXT_LEN:
            break
        parts.append(section)
        total_len += len(section)

    return "".join(parts)


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
    *,
    github_info: dict | None = None,
    locale: str = "en",
) -> dict:
    """Generate a fix guide using AI.

    Args:
        test_result: Full test result_json parsed dict.
        scenario_result: The specific failed scenario dict.
        target_url: The test target URL.
        ai_config: AIConfig object with provider/api_key/model.
        github_info: Optional {"pat", "owner", "repo", "branch"} for source context.
        locale: UI locale code (e.g. "ko", "en") → AI responds in this language.

    Returns:
        {"summary": ..., "files": [...]} or raises.
    """
    from aat.adapters import ADAPTER_REGISTRY

    adapter_cls = ADAPTER_REGISTRY.get(ai_config.provider)  # type: ignore[attr-defined]
    if adapter_cls is None:
        raise ValueError(f"Unknown AI provider: {ai_config.provider}")  # type: ignore[attr-defined]

    adapter = adapter_cls(ai_config)

    # Build source context from GitHub if available
    source_context = ""
    if github_info:
        try:
            tree = await _fetch_file_tree(
                github_info["pat"], github_info["owner"],
                github_info["repo"], github_info["branch"],
            )
            relevant = _identify_relevant_files(tree, scenario_result, target_url)
            if relevant:
                source_context = await _build_source_context(
                    github_info["pat"], github_info["owner"],
                    github_info["repo"], github_info["branch"],
                    tree, relevant,
                )
        except Exception:
            logger.warning("Source context fetch failed", exc_info=True)

    response_language = _LOCALE_TO_LANG.get(locale, locale or "English")

    prompt = FIX_GUIDE_PROMPT.format(
        scenario_name=scenario_result.get("scenario_name", "Unknown"),
        scenario_id=scenario_result.get("scenario_id", "unknown"),
        target_url=target_url,
        failed_steps=_format_failed_steps(scenario_result),
        source_context=source_context,
        response_language=response_language,
    )

    # Call adapter's _call_api — returns parsed JSON directly.
    # Ollama accepts (system, user_text: str); OpenAI/Claude accept
    # (system, user_content: list[dict]).
    system_prompt = "You are a code fix assistant. Respond only with valid JSON."
    from aat.adapters.ollama import OllamaAdapter

    if isinstance(adapter, OllamaAdapter):
        result = await adapter._call_api(system_prompt, prompt)  # noqa: SLF001
    else:
        user_content = [{"type": "text", "text": prompt}]
        result = await adapter._call_api(system_prompt, user_content)  # noqa: SLF001

    if not result:
        return {"summary": "AI returned no response.", "files": []}

    # _call_api returns parsed JSON (dict). If it's a string, try parsing.
    if isinstance(result, str):
        parsed = _extract_json(result)
        if parsed is None:
            logger.warning("Failed to parse AI fix guide response: %s", result[:200])
            return {"summary": result[:500], "files": []}
        result = parsed

    # Validate structure
    if "summary" not in result:
        result["summary"] = "AI analysis complete."
    if "files" not in result:
        result["files"] = []

    return result
