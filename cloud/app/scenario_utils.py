"""Shared scenario utilities — used by scan.py, tests.py, executor.py.

Extracted to avoid cross-imports between routers and keep
common logic (compression, validation, form-submit fix) in one place.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_AI_MODELS: dict[str, str] = {
    "claude": "claude-sonnet-4-20250514",
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "ollama": "codellama:7b",
    "zhipuai": "glm-4-flash",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_json(text: str | None) -> Any:
    """Safely parse JSON text."""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Observation compression
# ---------------------------------------------------------------------------

def _extract_path(url: str, base_url: str = "") -> str:
    """Extract path from URL, stripping base to save tokens."""
    if not url:
        return ""
    if base_url and url.startswith(base_url):
        path = url[len(base_url):]
        return path if path else "/"
    # Strip scheme+host
    if "://" in url:
        after = url.split("://", 1)[1]
        slash = after.find("/")
        return after[slash:] if slash >= 0 else "/"
    return url


def _element_tag(elem: dict) -> str:
    """Convert element dict to compact tag: TYPE:selector|'text'."""
    etype = elem.get("type", "")
    sel = elem.get("selector", "?")
    txt = elem.get("text", "")
    tag = {
        "link": "LINK", "button": "BTN", "submit_button": "SUBMIT",
        "nav_item": "NAV", "input": "INPUT",
    }.get(etype, etype.upper() if etype else "EL")
    return f"{tag}:{sel}|'{txt}'"


def _field_tag(f: dict) -> str:
    """Convert form field to compact tag."""
    sel = f.get("selector", "?")
    if f.get("type") == "submit_button":
        ctx = f.get("context", "")
        ctx_tag = f"[{ctx}]" if ctx else ""
        label = f.get("label", "")
        return f"SUBMIT{ctx_tag}:{sel}|'{label}'"
    ftype = f.get("type", "text")
    ph = f.get("placeholder", "") or f.get("label", "")
    return f"INPUT:{ftype}:{sel}|'{ph}'"


def _change_tag(ct: str, after_path: str) -> str:
    """Convert change type to compact arrow notation."""
    if ct == "page_navigation":
        return f"→nav:{after_path}"
    if ct == "modal_opened":
        return "→modal"
    if ct == "content_expanded":
        return "→expand"
    if ct == "anchor_scroll":
        return "→scroll"
    if ct == "section_change":
        return "→section"
    if ct == "element_change":
        return "→changed"
    if ct == "file_download":
        return f"→download:{after_path}"
    return f"→{ct}"


def compress_observations_for_ai(
    observations: list[dict],
    max_tokens: int = 15000,
) -> str:
    """Compress observation data into compact tagged format within token budget.

    Format: [N] TAG:selector|'text' →change_type:path | texts:[...]
    Fields:  INPUT:type:selector|'placeholder', SUBMIT[ctx]:selector|'label'
    """
    if not observations:
        return "No observations collected."

    # Estimate uncompressed size for logging
    raw_json = json.dumps(observations, ensure_ascii=False)
    raw_tokens = len(raw_json) // 3

    # 1) Deduplicate by selector+text
    seen: set[str] = set()
    unique_obs: list[dict] = []
    for obs in observations:
        elem = obs.get("element", {})
        key = f"{elem.get('selector', '')}|{elem.get('text', '').lower()}"
        if key not in seen:
            seen.add(key)
            unique_obs.append(obs)

    # 2) Priority sort (forms/modal > navigation > static)
    def _priority(obs: dict) -> int:
        change = obs.get("observed_change", {})
        ct = change.get("type", "")
        if change.get("modal_form_fields") or change.get("navigated_page_fields"):
            return 0
        if ct == "modal_opened":
            return 1
        if ct == "page_navigation":
            return 2
        if ct == "content_expanded":
            return 3
        if ct in ("anchor_scroll", "section_change"):
            return 4
        return 5
    unique_obs.sort(key=_priority)

    # Detect base URL for path extraction
    base_url = ""
    for obs in unique_obs:
        before = obs.get("before", {}).get("url", "")
        if before and "://" in before:
            parts = before.split("://", 1)
            host_end = parts[1].find("/")
            base_url = f"{parts[0]}://{parts[1][:host_end]}" if host_end >= 0 else before
            break

    # 3) Build compact lines
    lines: list[str] = []
    all_assert_texts: list[str] = []
    all_element_texts: list[str] = []

    for idx, obs in enumerate(unique_obs, 1):
        elem = obs.get("element", {})
        change = obs.get("observed_change", {})
        ct = change.get("type", "no_change")
        if ct == "no_change":
            continue

        txt = elem.get("text", "")
        if txt:
            all_element_texts.append(txt)

        after_url = obs.get("after", {}).get("url", "")
        after_path = _extract_path(after_url, base_url)
        new_text = change.get("new_text", [])

        # Collect assert texts
        for nt in new_text:
            if nt and nt.strip():
                all_assert_texts.append(nt.strip())

        # Main line: [N] TAG:sel|'text' →change:path | texts:[...]
        parts = [f"[{idx}] {_element_tag(elem)} {_change_tag(ct, after_path)}"]
        if new_text:
            # Limit to 5 items, compact JSON
            texts_compact = json.dumps(new_text[:5], ensure_ascii=False, separators=(",", ":"))
            parts.append(f"texts:{texts_compact}")
        line = " | ".join(parts)

        # Auth pattern inline
        auth_info = obs.get("auth_pattern")
        if auth_info:
            pt = auth_info.get("page_type", "")
            if pt:
                line += f" AUTH:{pt}"

        lines.append(line)

        # Form fields inline (indented under parent)
        modal_fields = change.get("modal_form_fields", [])
        nav_fields = change.get("navigated_page_fields", [])
        for fields, label in [(modal_fields, "MODAL"), (nav_fields, "PAGE")]:
            if fields:
                ftags = [_field_tag(f) for f in fields]
                lines.append(f"  {label}: {', '.join(ftags)}")

    # 4) Build result
    def _build_result() -> str:
        result_parts = ["## OBS"]
        result_parts.extend(lines)
        if all_assert_texts:
            texts_json = json.dumps(
                list(dict.fromkeys(all_assert_texts)),  # dedup preserving order
                ensure_ascii=False, separators=(",", ":"),
            )
            result_parts.append(f"ASSERT_TEXTS:{texts_json}")
        return "\n".join(result_parts)

    result = _build_result()
    estimated_tokens = len(result) // 3

    while estimated_tokens > max_tokens and lines:
        lines.pop()
        result = _build_result()
        estimated_tokens = len(result) // 3

    compressed_tokens = len(result) // 3
    if raw_tokens > 0:
        reduction = (1 - compressed_tokens / raw_tokens) * 100
        logger.info(
            "Observation compressed: %s → %s tokens (-%s%%)",
            f"{raw_tokens:,}", f"{compressed_tokens:,}", f"{reduction:.0f}",
        )

    return result


def compress_crawl_data(crawl_data: dict, max_chars: int = 12000) -> str:
    """Compress crawl data (nav_menus, forms, buttons) into compact format.

    Instead of raw JSON, uses tagged format:
    FORM: selector | fields: INPUT:type:sel|'ph', SUBMIT:sel|'label'
    BTN: selector|'text'
    NAV: text→href, text→href
    """
    parts: list[str] = []

    # Nav menus — compact: just text→href pairs
    nav_menus = crawl_data.get("nav_menus", [])
    if nav_menus:
        items: list[str] = []
        seen_nav: set[str] = set()
        for menu in nav_menus:
            for item in menu.get("items", []):
                txt = item.get("text", "")
                href = item.get("href", "")
                key = f"{txt}|{href}"
                if key not in seen_nav and txt:
                    seen_nav.add(key)
                    items.append(f"'{txt}'→{href}")
        if items:
            parts.append(f"NAV: {', '.join(items[:15])}")

    # Forms — compact: selector + fields
    forms = crawl_data.get("forms", [])
    for form in forms:
        f_sel = form.get("selector", "form")
        fields = form.get("fields", [])
        submit = form.get("submit_button", {})

        ftags: list[str] = []
        for f in fields:
            ftags.append(_field_tag(f))
        if submit:
            s_sel = submit.get("selector", "?")
            s_txt = submit.get("text", "")
            ftags.append(f"SUBMIT:{s_sel}|'{s_txt}'")

        parts.append(f"FORM({f_sel}): {', '.join(ftags)}")

    # Buttons — compact list
    buttons = crawl_data.get("buttons", [])
    if buttons:
        btn_strs = [
            f"BTN:{b.get('selector', '?')}|'{b.get('text', '')}'"
            for b in buttons[:20]
        ]
        parts.append(f"BTNS: {', '.join(btn_strs)}")

    # Links (if present)
    links = crawl_data.get("links", [])
    if links:
        link_strs = [
            f"'{lnk.get('text', '')}'→{lnk.get('href', '')}"
            for lnk in links[:10]
            if lnk.get("text", "").strip()
        ]
        if link_strs:
            parts.append(f"LINKS: {', '.join(link_strs)}")

    result = "\n".join(parts)

    # Truncate if over budget
    if len(result) > max_chars:
        result = result[:max_chars] + "\n...(truncated)"

    # Log compression
    raw_json = json.dumps(crawl_data, ensure_ascii=False)
    raw_tokens = len(raw_json) // 3
    compressed_tokens = len(result) // 3
    if raw_tokens > 0:
        reduction = (1 - compressed_tokens / raw_tokens) * 100
        logger.info(
            "Crawl data compressed: %s → %s tokens (-%s%%)",
            f"{raw_tokens:,}", f"{compressed_tokens:,}", f"{reduction:.0f}",
        )

    return result


# ---------------------------------------------------------------------------
# Scenario validation
# ---------------------------------------------------------------------------

def _find_closest(
    target: str, candidates: set[str],
) -> str | None:
    """Find the most similar string from candidates."""
    if not candidates:
        return None
    best = None
    best_score = 0
    for c in candidates:
        common = sum(1 for ch in target if ch in c)
        score = common / max(len(target), len(c), 1)
        if score > best_score:
            best_score = score
            best = c
    return best if best_score > 0.3 else None


def validate_scenarios(
    scenarios: list,
    observations: list[dict],
    page_data: list[dict] | None = None,
) -> list[dict]:
    """Validate scenario step targets against observation/crawl data.

    Returns list of validation results per step:
    [{"scenario_idx": 0, "step": 1, "status": "verified"|"unverified",
      "target_text": "...", "closest_match": "..."|null}]
    """
    observed_texts: set[str] = set()
    observed_selectors: set[str] = set()
    observed_urls: set[str] = set()
    form_fields: set[str] = set()

    for obs in observations:
        elem = obs.get("element", {})
        txt = (elem.get("text") or "").strip().lower()
        sel = (elem.get("selector") or "").strip().lower()
        if txt:
            observed_texts.add(txt)
        if sel:
            observed_selectors.add(sel)
        for nt in obs.get("observed_change", {}).get("new_text", []):
            nt_lower = nt.strip().lower()
            if nt_lower:
                observed_texts.add(nt_lower)
        for key in ("before", "after"):
            u = obs.get(key, {}).get("url", "")
            if u:
                observed_urls.add(u.lower())

    for pdata in (page_data or []):
        for nav in pdata.get("nav_menus", []):
            for item in nav.get("items", []):
                txt = (item.get("text") or "").strip().lower()
                if txt:
                    observed_texts.add(txt)
        for btn in pdata.get("buttons", []):
            txt = (btn.get("text") or "").strip().lower()
            if txt:
                observed_texts.add(txt)
        for link in pdata.get("links", []):
            txt = (link.get("text") or "").strip().lower()
            href = (link.get("href") or "").lower()
            if txt:
                observed_texts.add(txt)
            if href:
                observed_urls.add(href)
        for form in pdata.get("forms", []):
            for field in form.get("fields", []):
                for fkey in ("name", "placeholder", "label", "aria_label"):
                    val = (field.get(fkey) or "").strip().lower()
                    if val:
                        form_fields.add(val)
                        observed_texts.add(val)
                sel = (field.get("selector") or "").strip().lower()
                if sel:
                    observed_selectors.add(sel)

    results: list[dict] = []

    for si, scenario in enumerate(scenarios):
        steps = []
        if hasattr(scenario, "steps"):
            steps = scenario.steps
        elif isinstance(scenario, dict):
            steps = scenario.get("steps", [])

        for step in steps:
            if hasattr(step, "target"):
                target_obj = step.target
                action = (
                    step.action.value
                    if hasattr(step.action, "value")
                    else str(step.action)
                )
                step_num = step.step
                target_text = (
                    target_obj.text if target_obj else None
                )
                value = step.value
            else:
                target_obj = step.get("target")
                action = str(step.get("action", ""))
                step_num = step.get("step", 0)
                target_text = (
                    target_obj.get("text") if target_obj else None
                )
                value = step.get("value")

            if action in ("navigate", "wait", "screenshot"):
                if action == "navigate" and value:
                    results.append({
                        "scenario_idx": si,
                        "step": step_num,
                        "status": "verified",
                        "target_text": value,
                    })
                continue

            if not target_text:
                continue

            tt_lower = target_text.strip().lower()

            if tt_lower in observed_texts:
                results.append({
                    "scenario_idx": si,
                    "step": step_num,
                    "status": "verified",
                    "target_text": target_text,
                })
                continue

            partial = None
            for ot in observed_texts:
                if tt_lower in ot or ot in tt_lower:
                    partial = ot
                    break

            if partial:
                results.append({
                    "scenario_idx": si,
                    "step": step_num,
                    "status": "verified",
                    "target_text": target_text,
                    "closest_match": partial,
                })
                continue

            if tt_lower in form_fields:
                results.append({
                    "scenario_idx": si,
                    "step": step_num,
                    "status": "verified",
                    "target_text": target_text,
                })
                continue

            closest = _find_closest(tt_lower, observed_texts)
            results.append({
                "scenario_idx": si,
                "step": step_num,
                "status": "unverified",
                "target_text": target_text,
                "closest_match": closest,
            })

    return results


_DELTA_SYSTEM = (
    "You are an expert QA engineer. Fix ONLY the broken steps listed below. "
    "Return a JSON object: {\"fixes\": [{\"scenario_idx\": 0, \"step\": 4, "
    "\"target\": {\"selector\": \"...\", \"text\": \"...\"}, \"value\": \"...\" | null}]}. "
    "Each fix replaces one step's target/value. Return ONLY valid JSON."
)


async def validate_and_retry(
    scenarios: list,
    observations: list[dict],
    page_data: list[dict] | None,
    adapter: Any,
    prompt_context: str,
    *,
    system_prompt: str | None = None,
) -> tuple[list, list[dict]]:
    """Validate scenarios and retry failed steps via Delta Correction.

    Instead of resending the entire prompt, only the broken steps + their
    observation context are sent to AI. This reduces retry tokens by ~70-80%.

    Returns (possibly_fixed_scenarios, validation_results).
    """
    results = validate_scenarios(scenarios, observations, page_data)
    unverified = [r for r in results if r["status"] == "unverified"]
    total_validated = len(results)

    if (
        total_validated > 0
        and len(unverified) / total_validated > 0.3
        and observations
    ):
        logger.info(
            "Delta Correction: %d/%d unverified, fixing individual steps",
            len(unverified), total_validated,
        )

        # Build compact delta prompt with only broken steps + relevant obs
        delta_prompt = "## DELTA CORRECTION — Fix broken steps only\n\n"
        delta_prompt += "Broken steps:\n"
        for uv in unverified:
            sc_idx = uv.get("scenario_idx", 0)
            step_num = uv["step"]
            closest = uv.get("closest_match")
            hint = f' (closest match: "{closest}")' if closest else ""
            sc_name = ""
            if 0 <= sc_idx < len(scenarios):
                sc_name = getattr(scenarios[sc_idx], "name", "")
            delta_prompt += (
                f"- Scenario {sc_idx} ({sc_name}), Step {step_num}: "
                f'target "{uv["target_text"]}" NOT FOUND{hint}\n'
            )

        # Include only relevant observations (compact)
        delta_prompt += "\nAvailable elements from observation:\n"
        seen_texts: set[str] = set()
        for obs in observations[:10]:
            el = obs.get("element", {})
            el_text = el.get("text", "")
            if el_text and el_text not in seen_texts:
                seen_texts.add(el_text)
                sel = el.get("selector", "")
                delta_prompt += f'  - text="{el_text}" selector="{sel}"\n'
            change = obs.get("observed_change", {})
            for field_key in ("modal_form_fields", "navigated_page_fields"):
                for f in change.get(field_key, []):
                    f_label = f.get("label") or f.get("placeholder") or f.get("name", "")
                    f_sel = f.get("selector", "")
                    if f_label and f_label not in seen_texts:
                        seen_texts.add(f_label)
                        delta_prompt += f'  - field="{f_label}" selector="{f_sel}" type={f.get("type", "")}\n'

        delta_prompt += (
            "\nReturn ONLY the fixes for the broken steps. "
            "Use selectors/text from the available elements above."
        )

        try:
            fix_data = await adapter._call_api(
                _DELTA_SYSTEM,
                [{"type": "text", "text": delta_prompt}],
            )
            fixes = fix_data.get("fixes", []) if isinstance(fix_data, dict) else []

            applied = 0
            for fix in fixes:
                sc_idx = fix.get("scenario_idx", 0)
                step_num = fix.get("step", 0)
                new_target = fix.get("target")
                if not new_target or sc_idx >= len(scenarios):
                    continue

                sc = scenarios[sc_idx]
                for s in sc.steps:
                    if s.step == step_num and s.target is not None:
                        if new_target.get("selector"):
                            s.target.__dict__["selector"] = new_target["selector"]
                        if new_target.get("text"):
                            s.target.__dict__["text"] = new_target["text"]
                        if fix.get("value") is not None:
                            s.__dict__["value"] = fix["value"]
                        applied += 1
                        break

            if applied:
                logger.info("Delta Correction: applied %d/%d fixes", applied, len(fixes))
                results = validate_scenarios(scenarios, observations, page_data)
            else:
                logger.warning("Delta Correction: no fixes applied from %d candidates", len(fixes))

        except Exception as exc:
            logger.warning("Delta Correction failed, falling back: %s", exc)
            # Fallback: full retry (legacy behavior)
            retry_prompt = (
                f"{prompt_context}\n\n"
                "## VALIDATION FAILED — FIX REQUIRED\n"
                "The following targets were NOT found:\n"
            )
            for uv in unverified:
                closest = uv.get("closest_match")
                hint = f' (closest: "{closest}")' if closest else ""
                retry_prompt += f'- Step {uv["step"]}: "{uv["target_text"]}"{hint}\n'
            retry_prompt += (
                "\nFix these targets. Return the complete corrected scenario JSON array."
            )
            try:
                fixed = await adapter.generate_scenarios(
                    retry_prompt, system_prompt=system_prompt,
                )
                if fixed:
                    scenarios = fixed
                    results = validate_scenarios(scenarios, observations, page_data)
            except Exception as exc2:
                logger.warning("Full retry also failed: %s", exc2)

    return scenarios, results


# ---------------------------------------------------------------------------
# Form-submit post-generation fix
# ---------------------------------------------------------------------------

def fix_form_submit_steps(
    scenarios: list,
    observations: list[dict],
) -> list:
    """Fix scenarios where form input is followed by a nav click.

    After find_and_type steps, the next click should be a form submit
    button (context=form), not a navigation link (context=nav).
    """
    form_submits: dict[str, dict] = {}
    all_submit_buttons: list[dict] = []
    for obs in observations:
        change = obs.get("observed_change", {})
        nav_fields = change.get("navigated_page_fields", [])
        if not nav_fields:
            continue
        elem_text = (obs.get("element", {}).get("text") or "").strip()
        for f in nav_fields:
            if f.get("type") == "submit_button":
                all_submit_buttons.append({
                    "obs_elem": elem_text,
                    "label": f.get("label"),
                    "selector": f.get("selector"),
                    "context": f.get("context"),
                })
                if f.get("context") == "form" and elem_text not in form_submits:
                    form_submits[elem_text] = {
                        "selector": f.get("selector", ""),
                        "label": f.get("label", ""),
                    }

    logger.debug(
        "=== FORM-SUBMIT FIX: all submit buttons found ===\n%s",
        json.dumps(all_submit_buttons, ensure_ascii=False, indent=2),
    )
    logger.debug(
        "=== FORM-SUBMIT FIX: form_submits (context=form) ===\n%s",
        json.dumps(form_submits, ensure_ascii=False, indent=2),
    )

    if not form_submits:
        logger.debug("=== FIX APPLIED: NO (no form submit buttons found) ===")
        return scenarios

    nav_labels: set[str] = set()
    for obs in observations:
        change = obs.get("observed_change", {})
        for f in change.get("navigated_page_fields", []):
            if f.get("type") == "submit_button" and f.get("context") == "nav":
                lbl = (f.get("label") or "").strip().lower()
                if lbl:
                    nav_labels.add(lbl)

    for obs in observations:
        elem = obs.get("element", {})
        elem_type = elem.get("type", "")
        if elem_type == "nav_item":
            t = (elem.get("text") or "").strip().lower()
            if t:
                nav_labels.add(t)

    logger.debug(
        "=== FORM-SUBMIT FIX: nav_labels (will be replaced) === %s",
        nav_labels,
    )

    for scenario in scenarios:
        steps = []
        if hasattr(scenario, "steps"):
            steps = scenario.steps
        elif isinstance(scenario, dict):
            steps = scenario.get("steps", [])

        last_was_input = False
        nav_click_text = ""

        for step in steps:
            action = (
                step.action.value
                if hasattr(step, "action") and hasattr(step.action, "value")
                else str(
                    getattr(step, "action", "")
                    or (step.get("action", "") if isinstance(step, dict) else "")
                )
            )
            target = (
                step.target
                if hasattr(step, "target")
                else (step.get("target") if isinstance(step, dict) else None)
            )

            if action == "find_and_click" and not last_was_input:
                target_text = ""
                if target:
                    target_text = (
                        target.text
                        if hasattr(target, "text")
                        else target.get("text", "")
                    ) or ""
                if target_text in form_submits:
                    nav_click_text = target_text

            if action == "find_and_type":
                last_was_input = True
                continue

            if action == "find_and_click" and last_was_input and target:
                target_text = (
                    target.text
                    if hasattr(target, "text")
                    else target.get("text", "")
                ) or ""
                tt_lower = target_text.strip().lower()

                is_nav_click = tt_lower in nav_labels

                form_btn = form_submits.get(nav_click_text) or (
                    next(iter(form_submits.values())) if form_submits else None
                )

                logger.debug(
                    "=== FORM-SUBMIT CHECK: after input, click='%s', "
                    "is_nav=%s, nav_click_text='%s', form_btn=%s ===",
                    target_text, is_nav_click, nav_click_text, form_btn,
                )

                if is_nav_click and form_btn:
                    btn_label = form_btn["label"]
                    btn_selector = form_btn["selector"]

                    if tt_lower != btn_label.strip().lower():
                        logger.warning(
                            "FORM-SUBMIT FIX: Replacing nav click '%s' "
                            "with form submit '%s' (%s)",
                            target_text, btn_label, btn_selector,
                        )
                        if hasattr(target, "text"):
                            target.text = btn_label
                            if hasattr(target, "selector") and btn_selector:
                                target.selector = btn_selector
                        elif isinstance(target, dict):
                            target["text"] = btn_label
                            if btn_selector:
                                target["selector"] = btn_selector

            last_was_input = False

    return scenarios


# ---------------------------------------------------------------------------
# Fix generic/wrong field targets → observed field data
# ---------------------------------------------------------------------------

# Mapping from generic English keywords to field type for matching
_FIELD_TYPE_HINTS: dict[str, list[str]] = {
    "email": ["email", "mail", "e-mail", "email address"],
    "password": [
        "password", "pass", "pw", "passwd",
    ],
    "confirm_password": [
        "confirm password", "password confirm", "re-enter", "retype",
        "confirm", "verify",
    ],
    "name": [
        "name", "nickname", "username", "full name", "fullname",
    ],
    "phone": [
        "phone", "tel", "telephone", "mobile", "contact",
    ],
}


def _classify_field_hint(text: str) -> str:
    """Classify a field target text into a type hint (email, password, etc.)."""
    t = text.strip().lower()
    # confirm_password must be checked BEFORE password
    for hint_type in ("confirm_password", "email", "password", "name", "phone"):
        for keyword in _FIELD_TYPE_HINTS[hint_type]:
            if keyword in t:
                return hint_type
    return "unknown"


def _classify_observed_field(field: dict) -> str:
    """Classify an observed form field by its attributes."""
    f_type = (field.get("type") or "").lower()
    selector = (field.get("selector") or "").lower()
    placeholder = (field.get("placeholder") or "").lower()
    label = (field.get("label") or "").lower()
    hint = f"{f_type} {selector} {placeholder} {label}"

    # Check confirm password first (label/placeholder usually has "확인"/"confirm")
    for kw in _FIELD_TYPE_HINTS["confirm_password"]:
        if kw in hint:
            return "confirm_password"

    if f_type == "email" or any(kw in hint for kw in _FIELD_TYPE_HINTS["email"]):
        return "email"
    if f_type == "password" or any(
        kw in hint for kw in _FIELD_TYPE_HINTS["password"]
    ):
        return "password"
    if f_type == "tel" or any(kw in hint for kw in _FIELD_TYPE_HINTS["phone"]):
        return "phone"
    if any(kw in hint for kw in _FIELD_TYPE_HINTS["name"]):
        return "name"

    return "unknown"


def fix_field_targets(
    scenarios: list,
    observations: list[dict],
) -> list:
    """Fix AI-generated find_and_type targets to use actual observed field data.

    When the AI generates generic targets like {text: "Email"} instead of
    actual observed selectors/placeholders, this maps them to real field data.
    Critical for:
    - Ensuring correct CSS selectors are used
    - Distinguishing password vs confirm password fields
    - Using Korean placeholders instead of English generic names
    """
    # 1) Collect all form fields from observations
    observed_fields: list[dict] = []
    for obs in observations:
        change = obs.get("observed_change", {})
        for fields_key in ("navigated_page_fields", "modal_form_fields"):
            for f in change.get(fields_key, []):
                if f.get("type") == "submit_button":
                    continue
                observed_fields.append(f)

    if not observed_fields:
        return scenarios

    # 2) Classify each observed field
    classified: dict[str, list[dict]] = {}
    for f in observed_fields:
        ftype = _classify_observed_field(f)
        classified.setdefault(ftype, []).append(f)

    # Track password field count for confirm password disambiguation
    password_fields = classified.get("password", [])
    confirm_fields = classified.get("confirm_password", [])

    # If we have 2+ password-type fields but none classified as confirm,
    # treat the second one as confirm password
    if len(password_fields) >= 2 and not confirm_fields:
        confirm_fields = [password_fields.pop()]
        classified["confirm_password"] = confirm_fields
        classified["password"] = password_fields

    logger.debug(
        "FIELD-TARGET FIX: observed fields classified: %s",
        {k: len(v) for k, v in classified.items()},
    )

    # 3) Fix each find_and_type step
    # Track which types have been used per scenario to handle
    # duplicate password → second one becomes confirm_password
    for scenario in scenarios:
        steps: list = []
        if hasattr(scenario, "steps"):
            steps = scenario.steps
        elif isinstance(scenario, dict):
            steps = scenario.get("steps", [])

        used_types: dict[str, int] = {}  # type → count of usage

        for step in steps:
            action = ""
            if hasattr(step, "action") and hasattr(step.action, "value"):
                action = step.action.value
            elif hasattr(step, "action"):
                action = str(step.action)
            elif isinstance(step, dict):
                action = step.get("action", "")

            if action != "find_and_type":
                continue

            # Get target
            target = None
            if hasattr(step, "target"):
                target = step.target
            elif isinstance(step, dict):
                target = step.get("target")

            if not target:
                continue

            # Get target text
            target_text = ""
            if hasattr(target, "text"):
                target_text = target.text or ""
            elif isinstance(target, dict):
                target_text = target.get("text", "")

            target_selector = ""
            if hasattr(target, "selector"):
                target_selector = target.selector or ""
            elif isinstance(target, dict):
                target_selector = target.get("selector", "")

            # Already has a selector → likely correct from observation data
            if target_selector:
                continue

            # Classify what the AI intended
            intended_type = _classify_field_hint(target_text)
            if intended_type == "unknown":
                continue

            # KEY FIX: if this is the 2nd "password" step and we have
            # a confirm_password field, reclassify it automatically
            if intended_type == "password":
                used_types["password"] = used_types.get("password", 0) + 1
                if (
                    used_types["password"] >= 2
                    and classified.get("confirm_password")
                ):
                    intended_type = "confirm_password"
                    logger.info(
                        "FIELD-TARGET FIX: 2nd password step '%s' "
                        "→ reclassified as confirm_password",
                        target_text,
                    )

            # Find matching observed field
            matches = classified.get(intended_type, [])
            if not matches:
                continue

            observed = matches[0]
            new_selector = observed.get("selector", "")
            new_text = (
                observed.get("placeholder")
                or observed.get("label")
                or target_text
            )

            if new_selector or new_text != target_text:
                logger.warning(
                    "FIELD-TARGET FIX: '%s' → selector='%s', text='%s' "
                    "(type=%s)",
                    target_text, new_selector, new_text, intended_type,
                )
                if hasattr(target, "text"):
                    target.text = new_text
                    if hasattr(target, "selector") and new_selector:
                        target.selector = new_selector
                elif isinstance(target, dict):
                    target["text"] = new_text
                    if new_selector:
                        target["selector"] = new_selector

    return scenarios


# ---------------------------------------------------------------------------
# Multi-step form order enforcement
# ---------------------------------------------------------------------------

_NEXT_KW = frozenset({"next", "continue", "proceed"})
_BACK_KW = frozenset({"previous", "back", "prev"})
_REG_KW = ("register", "signup", "sign up", "registration")


def _get_step_action(step: object) -> str:
    """Extract action string from StepConfig or dict."""
    if hasattr(step, "action") and hasattr(step.action, "value"):
        return step.action.value
    if hasattr(step, "action"):
        return str(step.action)
    if isinstance(step, dict):
        return step.get("action", "")
    return ""


def _get_step_target_text(step: object) -> str:
    """Extract target text from StepConfig or dict."""
    target = (
        getattr(step, "target", None)
        if not isinstance(step, dict)
        else step.get("target")
    )
    if not target:
        return ""
    if hasattr(target, "text"):
        return (target.text or "").strip()
    if isinstance(target, dict):
        return (target.get("text") or "").strip()
    return ""


def _get_step_target_selector(step: object) -> str:
    """Extract target selector from StepConfig or dict."""
    target = (
        getattr(step, "target", None)
        if not isinstance(step, dict)
        else step.get("target")
    )
    if not target:
        return ""
    if hasattr(target, "selector"):
        return (target.selector or "").strip()
    if isinstance(target, dict):
        return (target.get("selector") or "").strip()
    return ""


def _set_step_num(step: object, num: int) -> None:
    """Set step number on StepConfig or dict."""
    if isinstance(step, dict):
        step["step"] = num
    elif hasattr(step, "step"):
        # Pydantic v2 model — direct attribute set (no frozen config)
        step.__dict__["step"] = num


def _build_field_phase_map(
    multi_step_fields: list[list[dict]],
) -> dict[str, int]:
    """Map field identifiers (selector/name/label/placeholder) → phase number."""
    mapping: dict[str, int] = {}
    for phase, fields in enumerate(multi_step_fields, 1):
        for f in fields:
            if f.get("type") == "submit_button":
                continue
            for key in ("selector", "name", "label", "placeholder"):
                val = (f.get(key) or "").strip().lower()
                if val and val not in mapping:
                    mapping[val] = phase
    return mapping


def _match_phase(
    step: object,
    field_map: dict[str, int],
    multi_step_fields: list[list[dict]],
) -> int:
    """Determine which multi-step phase a form step belongs to."""
    # 1) Exact selector match
    sel = _get_step_target_selector(step).lower()
    if sel and sel in field_map:
        return field_map[sel]

    # 2) Exact text match
    text = _get_step_target_text(step).lower()
    if text and text in field_map:
        return field_map[text]

    # 3) Partial text match (prefer longer key matches)
    if text:
        best_phase = 0
        best_len = 0
        for key, phase in field_map.items():
            if (text in key or key in text) and len(key) > best_len:
                best_phase = phase
                best_len = len(key)
        if best_phase:
            return best_phase

    # 4) Type-based heuristic fallback
    hint = _classify_field_hint(text) if text else "unknown"
    if hint != "unknown":
        for phase, fields in enumerate(multi_step_fields, 1):
            for f in fields:
                if f.get("type") == "submit_button":
                    continue
                if _classify_observed_field(f) == hint:
                    return phase

    return 1  # default to phase 1


def _make_step(
    step_num: int,
    action: str,
    description: str,
    target_text: str = "",
    target_selector: str = "",
    value: str = "",
) -> object:
    """Create a StepConfig object for injected steps."""
    from aat.core.models import ActionType, StepConfig, TargetSpec

    target = None
    if target_text or target_selector:
        target = TargetSpec(
            text=target_text or None,
            selector=target_selector or None,
        )

    return StepConfig(
        step=step_num,
        action=ActionType(action),
        target=target,
        value=value or None,
        description=description,
    )


def enforce_multi_step_order(
    scenarios: list,
    multi_step_fields: list[list[dict]],
) -> list:
    """Enforce correct step ordering for multi-step registration scenarios.

    AI often ignores the STEP ORDER RULE, placing Step 2 fields before the
    "next" click. This function:
    1. Identifies registration scenarios
    2. Classifies each form step into its multi-step phase
    3. Rebuilds: Step1 fields → "next" click → wait → Step2 fields → submit → assert
    """
    if not multi_step_fields or len(multi_step_fields) < 2:
        return scenarios

    field_map = _build_field_phase_map(multi_step_fields)
    num_phases = len(multi_step_fields)

    # Extract submit buttons per phase (skip back/previous buttons)
    step_buttons: dict[int, dict] = {}
    for idx, fields in enumerate(multi_step_fields, 1):
        candidates = [
            f for f in fields if f.get("type") == "submit_button"
        ]
        if candidates:
            non_back = [
                c for c in candidates
                if not any(
                    kw in (c.get("label") or "").lower()
                    for kw in _BACK_KW
                )
            ]
            # Prefer non-back button; fallback to last candidate
            step_buttons[idx] = (
                non_back[0] if non_back else candidates[-1]
            )

    for scenario in scenarios:
        sc_name = ""
        if hasattr(scenario, "name"):
            sc_name = scenario.name or ""
        elif isinstance(scenario, dict):
            sc_name = scenario.get("name", "")

        if not any(kw in sc_name.lower() for kw in _REG_KW):
            continue

        steps: list = []
        if hasattr(scenario, "steps"):
            steps = scenario.steps
        elif isinstance(scenario, dict):
            steps = scenario.get("steps", [])

        if not steps:
            continue

        # --- Categorize existing steps ---
        prefix: list = []          # navigate, initial non-form steps
        phase_inputs: dict[int, list] = {}   # phase → find_and_type steps
        phase_clicks: dict[int, list] = {}   # phase → checkbox/field clicks
        suffix: list = []          # assert, wait at end

        in_form = False
        post_submit = False

        # Collect all submit button labels to detect AI-generated submits
        last_btn = step_buttons.get(num_phases)
        all_btn_labels = {
            (b.get("label") or "").strip().lower()
            for b in step_buttons.values()
        }

        for step in steps:
            action = _get_step_action(step)
            target_text = _get_step_target_text(step).lower()

            if post_submit:
                suffix.append(step)
                continue

            if action == "navigate":
                prefix.append(step)
                continue

            if action == "find_and_type":
                in_form = True
                phase = _match_phase(step, field_map, multi_step_fields)
                phase_inputs.setdefault(phase, []).append(step)
                continue

            if action == "find_and_click":
                # Drop transition clicks — "next"/"previous" (will rebuild)
                if any(kw in target_text for kw in _NEXT_KW):
                    continue
                if any(kw in target_text for kw in _BACK_KW):
                    continue

                # Drop AI-generated submit buttons (will force-inject)
                if any(lbl and lbl in target_text for lbl in all_btn_labels):
                    post_submit = True
                    continue

                # Checkbox / other field click in form section
                if in_form:
                    phase = _match_phase(
                        step, field_map, multi_step_fields,
                    )
                    phase_clicks.setdefault(phase, []).append(step)
                else:
                    prefix.append(step)
                continue

            if action in ("assert", "wait") and in_form:
                suffix.append(step)
                post_submit = True
                continue

            # Other actions (screenshot, etc.)
            if not in_form:
                prefix.append(step)
            else:
                suffix.append(step)

        # --- Rebuild steps in correct order ---
        new_steps: list = list(prefix)
        step_num = len(new_steps) + 1

        for phase in range(1, num_phases + 1):
            # Field inputs for this phase
            for s in phase_inputs.get(phase, []):
                _set_step_num(s, step_num)
                new_steps.append(s)
                step_num += 1

            # Checkbox / other clicks for this phase
            for s in phase_clicks.get(phase, []):
                _set_step_num(s, step_num)
                new_steps.append(s)
                step_num += 1

            # Inject missing checkbox clicks from multi_step_fields
            phase_fields = multi_step_fields[phase - 1]
            existing_sels = {
                _get_step_target_selector(s).lower()
                for s in phase_clicks.get(phase, [])
            }
            existing_texts = {
                _get_step_target_text(s).lower()
                for s in phase_clicks.get(phase, [])
            }
            for f in phase_fields:
                if f.get("type") != "checkbox":
                    continue
                f_sel = (f.get("selector") or "").lower()
                f_label = (f.get("label") or "").lower()
                if f_sel and f_sel in existing_sels:
                    continue
                if f_label and f_label in existing_texts:
                    continue
                # Missing checkbox — inject click
                new_steps.append(_make_step(
                    step_num, "find_and_click",
                    f"Check '{f.get('label', 'checkbox')}'",
                    target_text=f.get("label", ""),
                    target_selector=f.get("selector", ""),
                ))
                step_num += 1
                logger.info(
                    "MULTI-STEP ORDER: Injected missing checkbox "
                    "'%s' for phase %d",
                    f.get("label", "?"), phase,
                )

            if phase < num_phases:
                # Inject "next" click + wait between phases
                btn = step_buttons.get(phase)
                btn_text = (
                    btn.get("label", "next") if btn else "next"
                )
                btn_sel = (
                    btn.get("selector", "") if btn else ""
                )

                new_steps.append(_make_step(
                    step_num, "find_and_click",
                    f"Click '{btn_text}' to proceed to step {phase + 1}",
                    target_text=btn_text,
                    target_selector=btn_sel,
                ))
                step_num += 1

                new_steps.append(_make_step(
                    step_num, "wait",
                    f"Wait for step {phase + 1} to load",
                    value="1500",
                ))
                step_num += 1

        # Final submit button — ALWAYS use multi_step_fields data
        # (AI output is unpredictable; force correct button regardless)
        if last_btn:
            new_steps.append(_make_step(
                step_num, "find_and_click",
                "Submit registration form",
                target_text=last_btn.get("label", "Submit"),
                target_selector=last_btn.get("selector", ""),
            ))
            step_num += 1

        # Suffix — force-replace assert for registration redirect
        # Registration form submit redirects to login/main page.
        # AI often asserts form text ("step 1", "account info") instead.
        has_assert = any(
            _get_step_action(s) == "assert" for s in suffix
        )
        if has_assert:
            for s in suffix:
                if _get_step_action(s) != "assert":
                    _set_step_num(s, step_num)
                    new_steps.append(s)
                    step_num += 1
                    continue
                # Replace with url_contains /login (common redirect)
                new_steps.append(_make_step(
                    step_num, "assert",
                    "Verify registration success — page redirected",
                    value="/login",
                ))
                # Set assert_type to url_contains on the new step
                new_step = new_steps[-1]
                if hasattr(new_step, "assert_type"):
                    from aat.core.models import AssertType
                    new_step.__dict__["assert_type"] = (
                        AssertType.URL_CONTAINS
                    )
                step_num += 1
        else:
            for s in suffix:
                _set_step_num(s, step_num)
                new_steps.append(s)
                step_num += 1
            # No assert at all — inject one
            new_steps.append(_make_step(
                step_num, "wait",
                "Wait for registration redirect",
                value="2000",
            ))
            step_num += 1
            assert_step = _make_step(
                step_num, "assert",
                "Verify registration success — page redirected",
                value="/login",
            )
            if hasattr(assert_step, "assert_type"):
                from aat.core.models import AssertType
                assert_step.__dict__["assert_type"] = (
                    AssertType.URL_CONTAINS
                )
            new_steps.append(assert_step)
            step_num += 1

        # Randomize registration email to prevent duplicate account errors
        import time

        unique_email = f"awttest_{int(time.time()) % 100000}@example.com"
        for s in new_steps:
            action = _get_step_action(s)
            if action != "find_and_type":
                continue
            sel = _get_step_target_selector(s).lower()
            txt = _get_step_target_text(s).lower()
            if "email" in sel or "email" in txt:
                # Replace email value
                if isinstance(s, dict):
                    s["value"] = unique_email
                elif hasattr(s, "value"):
                    s.__dict__["value"] = unique_email

        # Replace steps in-place
        steps.clear()
        steps.extend(new_steps)

        logger.info(
            "MULTI-STEP ORDER: Rebuilt '%s' — %d phases, %d total steps"
            " (email=%s)",
            sc_name, num_phases, len(new_steps), unique_email,
        )

    return scenarios


# ---------------------------------------------------------------------------
# Login prefix injection for auth-required scenarios
# ---------------------------------------------------------------------------

_AUTH_SKIP_KW = (
    "login", "register", "signup",
    "sign up", "broken", "nav",
)
_AUTH_NEED_KW = (
    "post", "write", "comment",
    "profile", "setting", "mypage",
    "dashboard", "create", "edit", "delete",
)


def _extract_login_info(
    observations: list[dict],
) -> dict[str, str] | None:
    """Extract login form selectors from observation data.

    Returns dict with keys: nav_selector, nav_text, email_selector,
    password_selector, submit_selector, submit_text.
    Returns None if login form not found.
    """
    for obs in observations:
        auth = obs.get("auth_pattern")
        if not auth or auth.get("page_type") != "login":
            continue

        elem = obs.get("element", {})
        change = obs.get("observed_change", {})
        fields = (
            change.get("navigated_page_fields")
            or change.get("modal_form_fields")
            or []
        )
        if not fields:
            continue

        info: dict[str, str] = {
            "nav_selector": elem.get("selector", ""),
            "nav_text": elem.get("text", "login"),
        }

        for f in fields:
            ftype = (f.get("type") or "").lower()
            sel = f.get("selector", "")
            label = f.get("label", "")

            if ftype == "email" or "email" in sel.lower():
                info["email_selector"] = sel
            elif ftype == "password" or "password" in sel.lower():
                info["password_selector"] = sel
            elif ftype == "submit_button" and f.get("context") == "form":
                info["submit_selector"] = sel
                info["submit_text"] = f.get("label", "login")

        if info.get("email_selector") and info.get("password_selector"):
            return info

    return None


def inject_login_prefix(
    scenarios: list,
    observations: list[dict],
    auth_data: dict[str, str],
    target_url: str,
) -> list:
    """Prepend login steps to scenarios that require authentication.

    After session isolation (cookies cleared per scenario), scenarios like
    "create post" or "write comment" need a login prefix to work.

    Skips login/register/nav scenarios that don't need auth.
    """
    if not auth_data:
        return scenarios

    email = auth_data.get("email", "")
    password = auth_data.get("password", "")
    if not email or not password:
        return scenarios

    login_info = _extract_login_info(observations)
    if not login_info:
        logger.debug("inject_login_prefix: no login form found in observations")
        return scenarios

    for scenario in scenarios:
        sc_name = ""
        sc_tags: list[str] = []
        if hasattr(scenario, "name"):
            sc_name = scenario.name or ""
            sc_tags = list(getattr(scenario, "tags", []))
        elif isinstance(scenario, dict):
            sc_name = scenario.get("name", "")
            sc_tags = scenario.get("tags", [])

        name_lower = sc_name.lower()
        tags_str = " ".join(sc_tags).lower()
        combined = f"{name_lower} {tags_str}"

        # Skip scenarios that don't need login
        if any(kw in combined for kw in _AUTH_SKIP_KW):
            continue
        if not any(kw in combined for kw in _AUTH_NEED_KW):
            continue

        steps: list = []
        if hasattr(scenario, "steps"):
            steps = scenario.steps
        elif isinstance(scenario, dict):
            steps = scenario.get("steps", [])

        if not steps:
            continue

        # Check if login steps already exist (AI may have generated them)
        has_login = False
        for s in steps[:6]:
            t = _get_step_target_text(s).lower()
            if "login" in t:
                sel = _get_step_target_selector(s).lower()
                if "password" in sel or "email" in sel or "login" in sel:
                    has_login = True
                    break
        if has_login:
            continue

        # Build login prefix steps
        login_steps = [
            _make_step(1, "navigate", "Navigate to homepage",
                       value=target_url),
            _make_step(2, "find_and_click", "Click login link",
                       target_text=login_info.get("nav_text", "login"),
                       target_selector=login_info.get("nav_selector", "")),
            _make_step(3, "wait", "Wait for login form",
                       value="1000"),
            _make_step(4, "find_and_type", "Enter email",
                       target_text="email",
                       target_selector=login_info.get("email_selector", ""),
                       value=email),
            _make_step(5, "find_and_type", "Enter password",
                       target_text="password",
                       target_selector=login_info.get("password_selector", ""),
                       value=password),
            _make_step(6, "find_and_click", "Click login button",
                       target_text=login_info.get("submit_text", "login"),
                       target_selector=login_info.get("submit_selector", "")),
            _make_step(7, "wait", "Wait for login redirect",
                       value="1500"),
        ]

        # Renumber existing steps
        offset = len(login_steps)
        for s in steps:
            old_num = (
                s.step if hasattr(s, "step") and not isinstance(s, dict)
                else s.get("step", 0) if isinstance(s, dict) else 0
            )
            _set_step_num(s, old_num + offset)

        # Prepend login steps
        for ls in reversed(login_steps):
            steps.insert(0, ls)

        logger.info(
            "LOGIN PREFIX: Injected %d login steps into '%s'",
            len(login_steps), sc_name,
        )

    return scenarios


def ensure_post_submit_assert(scenarios: list) -> list:
    """Ensure every form scenario has wait+assert after the submit click.

    If find_and_type steps are followed by a submit click with no subsequent
    assert, insert a wait(1500) step so the post-submit page state is captured
    in screenshots. Logs a warning when this safety net triggers.
    """
    for scenario in scenarios:
        steps: list = []
        if hasattr(scenario, "steps"):
            steps = scenario.steps
        elif isinstance(scenario, dict):
            steps = scenario.get("steps", [])

        if not steps:
            continue

        def _get_action(step: object) -> str:
            if hasattr(step, "action") and hasattr(step.action, "value"):
                return step.action.value
            if hasattr(step, "action"):
                return str(step.action)
            if isinstance(step, dict):
                return step.get("action", "")
            return ""

        # Find the last submit click after form input
        has_type = False
        last_submit_idx = -1
        for i, step in enumerate(steps):
            action = _get_action(step)
            if action == "find_and_type":
                has_type = True
            elif action == "find_and_click" and has_type:
                last_submit_idx = i

        if last_submit_idx < 0:
            continue

        # Check if there's already an assert or wait after the submit
        has_post_submit = False
        for step in steps[last_submit_idx + 1:]:
            action = _get_action(step)
            if action in ("assert", "wait"):
                has_post_submit = True
                break

        if has_post_submit:
            continue

        # Safety net: insert wait step after submit for screenshot capture
        sc_name = ""
        if hasattr(scenario, "name"):
            sc_name = scenario.name
        elif isinstance(scenario, dict):
            sc_name = scenario.get("name", "")

        logger.warning(
            "POST-SUBMIT SAFETY: No assert after form submit in '%s' "
            "— inserting wait(1500) for screenshot capture",
            sc_name,
        )

        next_step_num = len(steps) + 1
        wait_step = {
            "step": next_step_num,
            "action": "wait",
            "value": "1500",
            "description": "Wait for page transition after form submit",
        }
        steps.append(wait_step)

    return scenarios


# ---------------------------------------------------------------------------
# Site language detection
# ---------------------------------------------------------------------------

_KO_RE = re.compile(r"[\uac00-\ud7a3]")


def detect_site_language(
    page_data: dict | None,
    observations: list[dict] | None = None,
) -> str:
    """Detect the primary language of the target site.

    Returns "ko", "en", or "auto" (unknown).

    Heuristic:
    1. HTML lang attribute from page data (most reliable)
    2. Count Korean characters vs Latin characters in observable text
    """
    if not page_data:
        return "auto"

    # 1) Check HTML lang attribute (set by crawler in page_data)
    html_lang = (page_data.get("html_lang") or "").lower().strip()
    if html_lang.startswith("ko"):
        return "ko"
    if html_lang.startswith("en"):
        return "en"

    # 2) Heuristic: sample text from buttons, links, nav, forms
    texts: list[str] = []
    for key in ("buttons", "links", "nav_menus"):
        for item in page_data.get(key, []):
            t = item.get("text", "") if isinstance(item, dict) else str(item)
            if t:
                texts.append(t)
    for form in page_data.get("forms", []):
        if isinstance(form, dict):
            for field in form.get("fields", []):
                for k in ("label", "placeholder"):
                    v = field.get(k, "")
                    if v:
                        texts.append(v)

    if observations:
        for obs in observations[:20]:
            elem = obs.get("element", {})
            t = elem.get("text", "")
            if t:
                texts.append(t)

    sample = " ".join(texts)
    if not sample:
        return "auto"

    ko_chars = len(_KO_RE.findall(sample))
    # If Korean characters make up > 10% of non-space chars, it's Korean
    non_space = len(sample.replace(" ", ""))
    if non_space > 0 and ko_chars / non_space > 0.10:
        return "ko"
    return "en"


def build_language_instruction(site_lang: str) -> str:
    """Build a prompt instruction for the AI about output language.

    Only emitted when the site is detected as English, to prevent
    Korean scenario text on English-language sites.
    """
    common_suffix = (
        "- NEVER generate scenarios that CHECK or VERIFY the page language itself.\n"
        '  WRONG: "Verify that page content is in English"\n'
        '  WRONG: "Verify page displays Korean text"\n'
        "  Language verification is NOT a valid E2E test.\n"
        "- ALL assert values MUST be EXACT text copied from page data or observations.\n"
        "  NEVER invent assert text — copy-paste only.\n"
    )
    if site_lang == "en":
        return (
            "\n## ========== LANGUAGE RULE (CRITICAL) ==========\n"
            "This is an ENGLISH-language website. ALL generated text MUST be in English:\n"
            "- Scenario names and descriptions: English\n"
            "- Step descriptions: English\n"
            "- Assert values (text_visible, url_contains): copy EXACT English text from data\n"
            "- Test data: use English (e.g., 'Test User', 'awttest@example.com')\n"
            "- Match form field labels and button text exactly as they appear.\n"
            + common_suffix
        )
    if site_lang == "ko":
        return (
            "\n## ========== LANGUAGE RULE ==========\n"
            "This is a KOREAN-language website. Use Korean for scenario names,\n"
            "descriptions, and test data where appropriate.\n"
            "Copy form field labels and button text EXACTLY as they appear in the data.\n"
            + common_suffix
        )
    return "\n" + common_suffix


# ---------------------------------------------------------------------------
# Assert step fix — validate and auto-correct malformed assert steps
# ---------------------------------------------------------------------------

def fix_assert_steps(scenarios: list) -> list:
    """Validate and fix assert steps that are missing required fields.

    AI sometimes generates assert steps without ``expected`` list or without
    ``assert_type`` + ``value``. This function patches them to prevent
    Pydantic validation errors.
    """
    for scenario in scenarios:
        steps: list = []
        if hasattr(scenario, "steps"):
            steps = scenario.steps
        elif isinstance(scenario, dict):
            steps = scenario.get("steps", [])

        for step in steps:
            is_dict = isinstance(step, dict)
            action = ""
            if is_dict:
                action = step.get("action", "")
            elif hasattr(step, "action"):
                action = (
                    step.action.value
                    if hasattr(step.action, "value")
                    else str(step.action)
                )

            if action != "assert":
                continue

            if is_dict:
                _fix_assert_dict(step)
            else:
                _fix_assert_obj(step)

        # Remove broken assert steps and renumber
        new_steps = [s for s in steps if not (isinstance(s, dict) and s.get("_remove"))]
        if len(new_steps) < len(steps):
            for i, s in enumerate(new_steps, 1):
                if isinstance(s, dict):
                    s["step"] = i
            if isinstance(scenario, dict):
                scenario["steps"] = new_steps
            elif hasattr(scenario, "steps"):
                scenario.steps = new_steps

    return scenarios


def _fix_assert_dict(step: dict) -> None:
    """Fix a dict-form assert step in-place."""
    has_expected = bool(step.get("expected"))
    has_assert_type = bool(step.get("assert_type"))
    has_value = bool(step.get("value"))

    if has_expected and has_assert_type:
        return  # already valid

    # Case 1: has assert_type + value but no expected list → build expected
    if has_assert_type and has_value and not has_expected:
        step["expected"] = [{
            "type": step["assert_type"],
            "value": step["value"],
            "tolerance": 0.0,
            "case_insensitive": True,
        }]
        return

    # Case 2: has expected list but no assert_type → derive from first item
    if has_expected and not has_assert_type:
        first = step["expected"][0]
        if isinstance(first, dict) and first.get("type"):
            step["assert_type"] = first["type"]
        elif isinstance(first, str):
            step["assert_type"] = "text_visible"
            step["expected"] = [{
                "type": "text_visible",
                "value": first,
                "tolerance": 0.0,
                "case_insensitive": True,
            }]
        return

    # Case 3: has value but no assert_type and no expected → infer type
    if has_value and not has_assert_type and not has_expected:
        val = step["value"]
        is_url = val.startswith("/") or val.startswith("http")
        at = "url_contains" if is_url else "text_visible"
        step["assert_type"] = at
        step["expected"] = [{
            "type": at,
            "value": val,
            "tolerance": 0.0,
            "case_insensitive": True,
        }]
        return

    # Case 4: nothing useful — mark for removal
    desc = step.get("description", "")
    logger.warning(
        "Assert step has no assert_type/expected/value — removing: '%s'",
        desc[:60],
    )
    step["_remove"] = True


def _fix_assert_obj(step: object) -> None:
    """Fix an object-form (Pydantic model) assert step in-place."""
    assert_type = getattr(step, "assert_type", None)
    expected = getattr(step, "expected", None) or []
    value = getattr(step, "value", None)

    if expected and assert_type:
        return

    if assert_type and value and not expected:
        step.__dict__["expected"] = [{
            "type": assert_type if isinstance(assert_type, str) else assert_type.value,
            "value": value,
            "tolerance": 0.0,
            "case_insensitive": True,
        }]
        return

    if expected and not assert_type:
        first = expected[0]
        if hasattr(first, "type"):
            step.__dict__["assert_type"] = first.type
        elif isinstance(first, dict) and first.get("type"):
            step.__dict__["assert_type"] = first["type"]

    if value and not assert_type and not expected:
        is_url = value.startswith("/") or value.startswith("http")
        at = "url_contains" if is_url else "text_visible"
        step.__dict__["assert_type"] = at
        step.__dict__["expected"] = [{
            "type": at,
            "value": value,
            "tolerance": 0.0,
            "case_insensitive": True,
        }]


# ---------------------------------------------------------------------------
# Assert auto-validation layer
# ---------------------------------------------------------------------------

# URL paths commonly guessed by AI without observation evidence
_GUESSED_URL_PATHS = {"/dashboard", "/home", "/main", "/index", "/welcome"}


def _extract_site_wide_texts(page_data: list[dict]) -> set[str]:
    """Extract texts that appear on all/most pages (nav items, title, logo).

    These are unreliable for login-success assertions because they are
    visible both before and after login.
    """
    texts: set[str] = set()
    titles: list[str] = []
    for p in page_data:
        # Navigation menu items — present on every page
        for menu in p.get("nav_menus", []):
            for item in menu.get("items", []):
                t = (item.get("text") or "").strip()
                if t:
                    texts.add(t.lower())
        # Collect titles for common-prefix extraction
        title = (p.get("title") or "").strip()
        if title:
            titles.append(title.lower())
        # Also extract heading texts (h1, h2) that appear on the page
        # These are often site names / logos visible on every page
        for heading in p.get("headings", []):
            h_text = (heading.get("text") or "").strip()
            if h_text and len(h_text) >= 3:
                texts.add(h_text.lower())

    # Extract common title prefix (site name) across pages
    # e.g., ["swag labs - login", "swag labs - products"] → "swag labs"
    if len(titles) >= 2:
        prefix = titles[0]
        for t in titles[1:]:
            while prefix and not t.startswith(prefix):
                prefix = prefix[:-1]
        # Clean trailing separators (-, |, :, spaces)
        prefix = prefix.rstrip(" -|:").strip()
        if prefix and len(prefix) >= 3:
            texts.add(prefix)
    elif titles:
        texts.add(titles[0])

    logger.info(
        "_extract_site_wide_texts: %d pages, titles=%s, result=%s",
        len(page_data), titles, texts,
    )
    return texts


def _extract_placeholder_texts(page_data: list[dict]) -> set[str]:
    """Extract form field placeholders/labels from page data.

    These should never be used as text_visible assert values because
    placeholders are inside input elements, not visible page text.
    """
    texts: set[str] = set()
    for p in page_data:
        for form in p.get("forms", []):
            for field in form.get("fields", []):
                for key in ("placeholder", "label"):
                    t = (field.get(key) or "").strip()
                    if t and len(t) >= 3:
                        texts.add(t.lower())
    return texts


def _extract_observed_urls(observations: list[dict]) -> set[str]:
    """Extract URLs actually seen in observation after.url fields."""
    urls: set[str] = set()
    for obs in observations:
        after = obs.get("after", {})
        if isinstance(after, dict):
            url = after.get("url") or ""
            if url:
                from urllib.parse import urlparse
                path = urlparse(url).path
                if path:
                    urls.add(path)
    return urls


def _is_login_scenario(scenario: dict | object) -> bool:
    """Check if a scenario is login-related based on name/description."""
    name = ""
    desc = ""
    if isinstance(scenario, dict):
        name = (scenario.get("name") or "").lower()
        desc = (scenario.get("description") or "").lower()
    else:
        name = (getattr(scenario, "name", "") or "").lower()
        desc = (getattr(scenario, "description", "") or "").lower()
    keywords = ("login", "signin", "sign in", "sign-in", "auth")
    return any(k in name or k in desc for k in keywords)


def _get_login_page_path(scenario: dict | object) -> str:
    """Extract login page URL path from navigate step."""
    steps: list = []
    if isinstance(scenario, dict):
        steps = scenario.get("steps", [])
    elif hasattr(scenario, "steps"):
        steps = scenario.steps or []

    for step in steps:
        action = ""
        if isinstance(step, dict):
            action = step.get("action", "")
        elif hasattr(step, "action"):
            action = (
                step.action.value
                if hasattr(step.action, "value")
                else str(step.action)
            )
        if action == "navigate":
            val = ""
            if isinstance(step, dict):
                val = step.get("value", "")
            elif hasattr(step, "value"):
                val = step.value or ""
            if val:
                from urllib.parse import urlparse
                return urlparse(val).path or "/"
    return "/"


def _find_post_login_url(
    observed_urls: set[str], login_page_path: str,
) -> str:
    """Find a likely post-login URL from observed URLs.

    Returns the best candidate path (not the login page itself),
    or empty string if none found.
    """
    candidates = [
        u for u in observed_urls
        if u != login_page_path and u != "/" and len(u) > 1
    ]
    if not candidates:
        return ""
    # Prefer paths with common post-login keywords
    for kw in ("inventory", "dashboard", "home", "main", "board", "index"):
        for c in candidates:
            if kw in c.lower():
                return c
    # Otherwise return the first non-login path
    return sorted(candidates)[0]


def _set_assert_fields(
    step: dict | object, is_dict: bool,
    assert_type: str, value: str,
) -> None:
    """Set assert_type, value, and expected on a step."""
    expected = [{
        "type": assert_type,
        "value": value,
        "tolerance": 0.0,
        "case_insensitive": True,
    }]
    if is_dict:
        step["assert_type"] = assert_type  # type: ignore[index]
        step["value"] = value  # type: ignore[index]
        step["expected"] = expected  # type: ignore[index]
    else:
        step.__dict__["assert_type"] = assert_type
        step.__dict__["value"] = value
        step.__dict__["expected"] = expected


def validate_asserts(
    scenarios: list,
    observations: list[dict] | None = None,
    page_data: list[dict] | None = None,
) -> list:
    """Validate and auto-fix assert steps after scenario generation.

    Checks applied to each assert step:
    (a) Must have assert_type AND value — remove if missing.
    (b) value == description — meaningless, remove.
    (c-1) url_not_contains with "/" or empty — useless, convert or remove.
    (c-2) url_contains with guessed path not in observed URLs — convert.
    (d) text_visible with site-wide text (nav items, page title)
        → remove for login scenarios (unreliable).
    (e) text_visible with form placeholder text — remove.

    Returns the (possibly modified) scenarios list.
    """
    observations = observations or []
    page_data = page_data or []

    site_wide_texts = _extract_site_wide_texts(page_data)
    placeholder_texts = _extract_placeholder_texts(page_data)
    observed_urls = _extract_observed_urls(observations)

    logger.info(
        "validate_asserts: site_wide_texts=%s, placeholder_texts=%s, "
        "observed_urls=%s, page_data_count=%d",
        site_wide_texts, placeholder_texts, observed_urls, len(page_data),
    )

    removed_count = 0
    converted_count = 0

    for sc_idx, scenario in enumerate(scenarios):
        steps: list = []
        if isinstance(scenario, dict):
            steps = scenario.get("steps", [])
        elif hasattr(scenario, "steps"):
            steps = scenario.steps or []

        is_login = _is_login_scenario(scenario)
        login_page_path = _get_login_page_path(scenario) if is_login else "/"

        for step in steps:
            is_dict = isinstance(step, dict)
            action = ""
            if is_dict:
                action = step.get("action", "")
            elif hasattr(step, "action"):
                action = (
                    step.action.value
                    if hasattr(step.action, "value")
                    else str(step.action)
                )

            if action != "assert":
                continue

            # --- Extract fields ---
            if is_dict:
                assert_type = step.get("assert_type", "")
                value = step.get("value", "")
                description = step.get("description", "")
            else:
                assert_type = getattr(step, "assert_type", "") or ""
                if hasattr(assert_type, "value"):
                    assert_type = assert_type.value
                value = getattr(step, "value", "") or ""
                description = getattr(step, "description", "") or ""

            sc_name = ""
            if isinstance(scenario, dict):
                sc_name = scenario.get("name", f"scenario-{sc_idx}")
            else:
                sc_name = getattr(scenario, "name", f"scenario-{sc_idx}")

            # (a) No assert_type or no value → mark for removal
            if not assert_type or not value:
                logger.warning(
                    "validate_asserts: removing assert without "
                    "assert_type/value in '%s': desc='%s'",
                    sc_name, description[:60],
                )
                if is_dict:
                    step["_remove"] = True
                removed_count += 1
                continue

            # (b) value == description → meaningless assert
            if value.strip() == description.strip() and value.strip():
                logger.warning(
                    "validate_asserts: removing assert where value equals "
                    "description in '%s': '%s'",
                    sc_name, value[:60],
                )
                if is_dict:
                    step["_remove"] = True
                removed_count += 1
                continue

            # (c-1) url_not_contains with useless value ("/" or empty)
            if assert_type == "url_not_contains" and is_login:
                val_stripped = value.strip()
                if val_stripped in ("", "/"):
                    # "/" matches every URL → useless. Try converting
                    # to url_contains with an observed post-login path.
                    post_login_url = _find_post_login_url(
                        observed_urls, login_page_path,
                    )
                    if post_login_url:
                        logger.info(
                            "validate_asserts: converting useless "
                            "url_not_contains '%s' → url_contains '%s' "
                            "in '%s'",
                            val_stripped, post_login_url, sc_name,
                        )
                        _set_assert_fields(
                            step, is_dict,
                            "url_contains", post_login_url,
                        )
                        converted_count += 1
                    else:
                        logger.warning(
                            "validate_asserts: removing useless "
                            "url_not_contains '%s' in '%s'",
                            val_stripped, sc_name,
                        )
                        if is_dict:
                            step["_remove"] = True
                        removed_count += 1
                    continue

            # (c-2) url_contains with guessed path
            if assert_type == "url_contains" and is_login:
                val_lower = value.strip().lower()
                if val_lower in _GUESSED_URL_PATHS and val_lower not in observed_urls:
                    # Try observed post-login URL first
                    post_login_url = _find_post_login_url(
                        observed_urls, login_page_path,
                    )
                    if post_login_url:
                        logger.info(
                            "validate_asserts: converting guessed "
                            "url_contains '%s' → url_contains '%s' "
                            "in '%s'",
                            value, post_login_url, sc_name,
                        )
                        _set_assert_fields(
                            step, is_dict,
                            "url_contains", post_login_url,
                        )
                    else:
                        new_value = (
                            login_page_path
                            if login_page_path != "/"
                            else "/login"
                        )
                        logger.info(
                            "validate_asserts: converting guessed "
                            "url_contains '%s' → url_not_contains '%s' "
                            "in '%s'",
                            value, new_value, sc_name,
                        )
                        _set_assert_fields(
                            step, is_dict,
                            "url_not_contains", new_value,
                        )
                    converted_count += 1
                    continue

            # (d) text_visible with site-wide text (login scenarios only)
            if assert_type == "text_visible" and is_login:
                val_lower = value.strip().lower()
                # Exact match OR substring: "swag labs" matches
                # "swag labs - login" and vice versa
                is_site_wide = val_lower in site_wide_texts or any(
                    val_lower in sw or sw in val_lower
                    for sw in site_wide_texts
                )
                if is_site_wide:
                    logger.warning(
                        "validate_asserts: removing login assert with "
                        "site-wide text '%s' in '%s' "
                        "(visible on login page too)",
                        value, sc_name,
                    )
                    if is_dict:
                        step["_remove"] = True
                    removed_count += 1
                    continue

            # (e) text_visible with form placeholder text
            if assert_type == "text_visible":
                val_lower = value.strip().lower()
                if val_lower in placeholder_texts:
                    logger.warning(
                        "validate_asserts: removing assert with "
                        "placeholder text '%s' in '%s'",
                        value, sc_name,
                    )
                    if is_dict:
                        step["_remove"] = True
                    removed_count += 1
                    continue

        # --- Remove marked steps and renumber ---
        new_steps = [
            s for s in steps
            if not (isinstance(s, dict) and s.get("_remove"))
        ]
        if len(new_steps) < len(steps):
            for i, s in enumerate(new_steps, 1):
                if isinstance(s, dict):
                    s["step"] = i
            if isinstance(scenario, dict):
                scenario["steps"] = new_steps
            elif hasattr(scenario, "steps"):
                scenario.steps = new_steps

    if removed_count or converted_count:
        logger.info(
            "validate_asserts summary: %d removed, %d converted",
            removed_count, converted_count,
        )

    return scenarios
