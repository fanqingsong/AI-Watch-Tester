"""aat devqa — fully automated test loop orchestrator.

Single command that controls the entire test cycle:
  URL detect → scan → scenario generate → run → fix → retry

The AI coding assistant only runs this command.
AWT handles everything else — no AI intervention in the loop.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import typer

from aat.core.config import load_config
from aat.core.exceptions import AATError

_MAX_ATTEMPTS = 5
_COMMON_PORTS = [3000, 8080, 5000, 4200, 8000, 5173, 3001, 8888, 9500]


def devqa_command(
    description: str = typer.Argument(
        help="Test description (e.g. 'login and dashboard test').",
    ),
    url: str | None = typer.Option(
        None,
        "--url",
        "-u",
        help="App URL (auto-detected if omitted).",
    ),
    config_path: str | None = typer.Option(None, "--config", "-c"),
    max_attempts: int = typer.Option(_MAX_ATTEMPTS, "--max-attempts", "-m"),
    fast: bool = typer.Option(
        False,
        "--fast",
        help="Enable fast mode: strictly use DOM matching, skip Vision/OCR fallbacks.",
    ),
    verbosity: str = typer.Option(
        "detailed",
        "--verbosity",
        "-V",
        help=(
            "Scenario verbosity: 'detailed' (60-80 steps, all verification) or "
            "'concise' (12-15 steps, core actions only)."
        ),
    ),
    screenshots: str = typer.Option(
        "all",
        "--screenshots",
        help=(
            "Screenshot strategy: 'all' (every step, default), "
            "'before-after' (action boundaries, ~70% fewer files), "
            "'on-failure' (failures only, CI/CD optimized)."
        ),
    ),
) -> None:
    """Run fully automated DevQA loop: scan → generate → test → fix → retry."""
    try:
        asyncio.run(
            _devqa(
                description,
                url,
                config_path,
                max_attempts,
                fast,
                verbosity,
                screenshots,
            )
        )
    except AATError as e:
        typer.echo(f"[AWT] Error: {e}", err=True)
        raise typer.Exit(code=1) from None


async def _devqa(
    description: str,
    url_override: str | None,
    config_path: str | None,
    max_attempts: int,
    fast_mode: bool = False,
    verbosity: str = "detailed",
    screenshots: str = "all",
) -> None:
    start_time = time.monotonic()
    cfg_path = Path(config_path) if config_path else None
    config = load_config(config_path=cfg_path)
    data_dir = Path(config.data_dir)

    typer.echo()
    typer.echo(f'[AWT] DevQA: "{description}"')
    typer.echo("[AWT] " + "=" * 50)

    # -- Step 1: Detect URL ---------------------------------------------------
    app_url: str = url_override or config.url or ""
    if not app_url:
        app_url = await _detect_url() or ""
    if not app_url:
        app_url = typer.prompt("[AWT] App URL not detected. Enter URL")
    typer.echo(f"[AWT] Target: {app_url}")

    # -- Step 2: Scan ---------------------------------------------------------
    typer.echo("[AWT] Step 1/4: Scanning...")
    scan_path = data_dir / "scan_result.json"
    compare_arg = str(scan_path) if scan_path.exists() else None
    _run_aat(["scan", "--url", app_url] + (["--compare", compare_arg] if compare_arg else []))

    if not scan_path.exists():
        typer.echo("[AWT] Scan failed — no scan_result.json")
        raise typer.Exit(code=1)

    scan_data = json.loads(scan_path.read_text("utf-8"))
    elem_count = scan_data.get("element_count", 0)
    typer.echo(f"[AWT] Scan complete: {elem_count} elements found")

    # -- Step 3: Generate scenario -------------------------------------------
    typer.echo("[AWT] Step 2/4: Generating scenario...")
    scenario_dir = Path("scenarios")
    scenario_dir.mkdir(exist_ok=True)

    scenario_yaml = _generate_scenario(
        description,
        scan_data,
        app_url,
        config.test_accounts,
        verbosity=verbosity,
    )
    # Extract generated ID for filename
    sc_id = _next_scenario_id()
    # Re-read from generated YAML (id already set by _generate_scenario)
    import re as _re

    m = _re.search(r"id:\s*['\"]?(SC-\d+)", scenario_yaml)
    if m:
        sc_id = m.group(1)
    scenario_path = scenario_dir / f"{sc_id.lower()}_devqa.yaml"
    scenario_path.write_text(scenario_yaml, encoding="utf-8")
    typer.echo(f"[AWT] Scenario: {scenario_path}")

    # Show scenario in human-readable form and wait for approval
    from aat.core.scenario_reviewer import ScenarioReviewer

    reviewer = ScenarioReviewer()
    if not reviewer.show_and_approve(
        scenario_yaml,
        scenario_path,
        attempt=1,
        auto_approve=False,  # devqa always requires human approval
    ):
        raise typer.Exit(code=0)

    # -- Step 4-6: Run + fix loop --------------------------------------------
    typer.echo("[AWT] Step 3/4: Testing...")
    passed = False
    attempt = 0

    for attempt in range(1, max_attempts + 1):
        typer.echo(f"\n[AWT] Attempt {attempt}/{max_attempts}")

        run_args = [
            "run",
            "--skill-mode",
            "--learn",
        ]
        if fast_mode:
            run_args.append("--fast")
        if verbosity != "detailed":
            run_args.extend(["--verbosity", verbosity])
        if screenshots != "all":
            run_args.extend(["--screenshots", screenshots])
        run_args.append(str(scenario_path))

        # Pass approval bypass via one-time token — user already approved above in this session
        import os as _os

        from aat.core.approval_token import ENV_VAR as _TOKEN_ENV
        from aat.core.approval_token import generate_token, store_token

        _token = generate_token()
        store_token(_token)
        env = {**_os.environ, _TOKEN_ENV: _token}
        exit_code = _run_aat(run_args, env=env)

        if exit_code == 0:
            passed = True
            break

        if attempt >= max_attempts:
            break

        # Fix: re-scan + update scenario
        typer.echo(f"[AWT] Fixing scenario (attempt {attempt})...")
        _run_aat(["scan", "--url", app_url, "--compare", str(scan_path)])

        # Reload scan data and regenerate
        scan_data = json.loads(scan_path.read_text("utf-8"))
        fail_info = _read_last_failure(data_dir)
        previous_yaml = scenario_yaml
        scenario_yaml = _fix_scenario(
            scenario_yaml,
            scan_data,
            fail_info,
            attempt,
        )
        scenario_path.write_text(scenario_yaml, encoding="utf-8")

        # Show diff + approval before retry
        from aat.core.scenario_reviewer import ScenarioReviewer

        if not ScenarioReviewer().show_and_approve(
            scenario_yaml,
            scenario_path,
            attempt=attempt + 1,
            previous_yaml=previous_yaml,
            auto_approve=False,  # always require human approval for retry
        ):
            typer.echo("[AWT] Retry cancelled.")
            raise typer.Exit(code=1)

    # -- Step 7/9: Report -----------------------------------------------------
    elapsed = (time.monotonic() - start_time) / 60
    typer.echo()
    typer.echo("[AWT] " + "=" * 50)
    if passed:
        typer.echo(f"[AWT] ✅ DevQA complete: ALL PASSED ({attempt} attempt(s), {elapsed:.1f}min)")
    else:
        typer.echo(f"[AWT] ❌ DevQA failed after {attempt} attempts ({elapsed:.1f}min)")
        _report_failure(data_dir)
        raise typer.Exit(code=1)
    typer.echo("[AWT] " + "=" * 50)


# -- URL detection ------------------------------------------------------------


async def _detect_url() -> str | None:
    """Check common localhost ports for a running server."""
    import httpx

    for port in _COMMON_PORTS:
        url = f"http://localhost:{port}"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(url)
                if resp.status_code < 500:
                    typer.echo(f"[AWT] Detected: {url} (HTTP {resp.status_code})")
                    return url
        except Exception:
            continue
    return None


# -- Scenario generation from scan data --------------------------------------


def _generate_scenario(
    description: str,
    scan_data: dict[str, Any],
    app_url: str,
    test_accounts: dict[str, dict[str, str]] | None = None,
    verbosity: str = "detailed",
) -> str:
    """Generate YAML scenario from scan_result.json elements.

    Smart generation:
    1. Detect form fields (input/textarea) and add fill steps
    2. Use test_accounts for login/signup flows
    3. Match description keywords to infer intent
    4. Validate: every input has a value, submit follows inputs

    verbosity:
        'detailed' — include assert_screen_changed after each click (default)
        'concise'  — omit assert/wait steps; aim for 12-15 core steps
    """
    import yaml

    elements = scan_data.get("elements", [])
    account = (test_accounts or {}).get("default", {})
    desc_lower = description.lower()

    steps: list[dict[str, Any]] = [
        {
            "step": 1,
            "action": "navigate",
            "value": app_url,
            "description": f"Open {app_url}",
        }
    ]
    step_num = 2

    # Classify elements — handle both DOM and Flutter Semantics
    is_flutter = scan_data.get("is_flutter", False)
    inputs = _classify_inputs(elements, is_flutter)
    buttons = [
        e
        for e in elements
        if e.get("type")
        in ("button", "a", "semantics", "label", "svg", "accessibility")  # Added "accessibility"
        and e.get("source") in ("dom", "semantics", "accessibility")  # Added "accessibility"
        and e.get("x", 0) > 100
        and e.get("role", "") not in ("textbox", "searchbox", "combobox")  # Exclude text input roles
        and e.get("y", 0) < 600  # Exclude footer elements (usually at bottom of page)
        and e.get("width", 0) > 0  # Exclude elements with zero width (invisible/invalid)
        and e.get("height", 0) > 0  # Exclude elements with zero height (invisible/invalid)
    ]

    # Detect intent from description
    intent = _detect_intent(desc_lower)

    # --- Form filling: add input steps before button clicks ---
    if intent in ("login", "signup", "search") or inputs:
        for inp_idx, inp in enumerate(inputs):
            value = _infer_input_value(inp, intent, account, description)
            if not value:
                continue

            target, extra = _build_input_target(
                inp,
                inp_idx,
                inputs,
                is_flutter,
            )
            if not target:
                continue

            step_dict: dict[str, Any] = {
                "step": step_num,
                "action": "find_and_type",
                "target": target,
                "value": value,
                "region": "main",
                "description": f"Enter {_input_description(inp)}",
            }
            step_dict.update(extra)

            steps.append(step_dict)
            step_num += 1

            # For search intent, add Enter key press instead of clicking button
            if intent == "search" and inp.get("role") in ("searchbox", "textbox"):
                steps.append(
                    {
                        "step": step_num,
                        "action": "press_key",
                        "value": "Enter",
                        "region": "main",
                        "description": "Press Enter to search",
                    }
                )
                step_num += 1

    # --- Button clicks: match keywords to buttons ---
    keywords = _extract_keywords(description)
    clicked_labels: set[str] = set()

    typer.echo(f"[DEBUG] Keywords extracted: {keywords}")
    typer.echo(f"[DEBUG] Available buttons: {[b['label'] for b in buttons[:5]]}")

    for kw in keywords:
        typer.echo(f"[DEBUG] Trying to match keyword: '{kw}'")
        matched = _find_matching_elements(kw, buttons)
        typer.echo(
            f"[DEBUG] Matched {len(matched)} elements for '{kw}': {[m['label'] for m in matched[:3]]}"
        )
        for el in matched[:1]:
            label = el["label"]
            if label in clicked_labels:
                continue
            clicked_labels.add(label)

            is_submit = _is_submit_button(el, intent)

            # Build target with accessibility priority
            target: dict[str, Any] = {"text": label}

            # Priority 0: Accessibility snapshot_ref (most reliable)
            if el.get("snapshot_ref") and el.get("source") == "accessibility":
                target["snapshot_ref"] = el["snapshot_ref"]
                if el.get("role"):
                    target["role"] = el["role"]
            # Priority 1: DOM selector
            elif el.get("selector") and el["source"] == "dom":
                target["selector"] = el["selector"]
            # Priority 2: Semantics (Flutter)
            elif el.get("source") == "semantics" and el.get("selector"):
                target["selector"] = el["selector"]

            click_step: dict[str, Any] = {
                "step": step_num,
                "action": "find_and_click",
                "target": target,
                "region": "main",
                "description": f'Click "{label}"',
            }
            if is_submit:
                click_step["critical"] = True

            steps.append(click_step)
            step_num += 1

            # Assert after click — detailed mode only
            if verbosity == "detailed":
                steps.append(
                    {
                        "step": step_num,
                        "action": "assert_screen_changed",
                        "threshold": 0.05,
                        "region": "main",
                        "description": f'Verify screen changed after "{label}"',
                    }
                )
                step_num += 1

    # --- Fallback: if no keywords matched, use prominent buttons ---
    if not clicked_labels:
        for el in buttons[:3]:
            label = el["label"]

            # Build target with accessibility priority
            target: dict[str, Any] = {"text": label}

            # Priority 0: Accessibility snapshot_ref (most reliable)
            if el.get("snapshot_ref") and el.get("source") == "accessibility":
                target["snapshot_ref"] = el["snapshot_ref"]
                if el.get("role"):
                    target["role"] = el["role"]
            # Priority 1: DOM selector
            elif el.get("selector") and el.get("source") == "dom":
                target["selector"] = el["selector"]
            # Priority 2: Semantics (Flutter)
            elif el.get("source") == "semantics" and el.get("selector"):
                target["selector"] = el["selector"]

            steps.append(
                {
                    "step": step_num,
                    "action": "find_and_click",
                    "target": target,
                    "region": "main",
                    "description": f'Click "{label}"',
                }
            )
            step_num += 1

    # --- Validate: ensure inputs before submit ---
    steps = _validate_form_flow(steps, inputs, account)

    # Final screenshot
    steps.append(
        {
            "step": len(steps) + 1,
            "action": "screenshot",
            "description": "Capture final state",
        }
    )

    # Re-number steps
    for i, s in enumerate(steps, 1):
        s["step"] = i

    scenario = {
        "id": _next_scenario_id(),
        "name": description,
        "description": f"Auto-generated from scan: {description}",
        "steps": steps,
    }

    return yaml.safe_dump(
        scenario,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


# -- Intent detection ---------------------------------------------------------


_INTENT_KEYWORDS: dict[str, list[str]] = {
    "login": ["login", "sign in", "signin", "log-in"],
    "signup": ["signup", "sign up", "register", "join"],
    "search": ["search", "find"],
    "generate": ["generate", "create", "make"],
}


def _classify_inputs(
    elements: list[dict[str, Any]],
    is_flutter: bool,
) -> list[dict[str, Any]]:
    """Classify input elements from scan data.

    Handles DOM inputs, Flutter Semantics textboxes, and Accessibility textboxes.
    Sorted by y-coordinate (top to bottom) for form order.
    """
    inputs: list[dict[str, Any]] = []

    for el in elements:
        el_type = el.get("type", "")
        role = el.get("role", "")

        # DOM inputs, Flutter Semantics, or Accessibility text inputs
        # Include: textbox, searchbox, combobox, and other text input roles
        if el_type in ("input", "textarea") or role in ("textbox", "searchbox", "combobox"):
            inputs.append(el)

    # Sort by y-coordinate (form order: top to bottom)
    inputs.sort(key=lambda e: (e.get("y", 0), e.get("x", 0)))
    return inputs


def _build_input_target(
    inp: dict[str, Any],
    inp_idx: int,
    all_inputs: list[dict[str, Any]],
    is_flutter: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build target dict for an input field.

    Returns (target_dict, extra_step_fields).
    Priority: Semantics label > input type selector > nth-of-type > match_index
    """
    target: dict[str, Any] = {}
    extra: dict[str, Any] = {}
    source = inp.get("source", "")
    label = str(inp.get("label", ""))
    role = inp.get("role", "")
    snapshot_ref = inp.get("snapshot_ref", "")

    # --- Priority 0: Snapshot reference (accessibility-based) ---
    if snapshot_ref and source == "accessibility":
        target["snapshot_ref"] = snapshot_ref
        if role:
            target["role"] = role
        if label:
            target["text"] = label
        return target, extra

    # --- Priority 1: Semantics aria-label (Flutter) ---
    if source == "semantics" and label:
        target["text"] = label
        # Use method: semantics to force Semantics lookup
        if is_flutter:
            extra["method"] = "semantics"
        return target, extra

    # --- Priority 2: input[type] selector (DOM) ---
    input_type = inp.get("input_type", "")
    if input_type and input_type not in ("text", ""):
        target["selector"] = f'input[type="{input_type}"]'
        if label:
            target["text"] = label
        return target, extra

    # --- Priority 3: nth-of-type (DOM, multiple generic inputs) ---
    if source == "dom":
        # Count how many inputs before this one
        y_sorted_dom = [e for e in all_inputs if e.get("source") == "dom"]
        position = next(
            (i for i, e in enumerate(y_sorted_dom) if e is inp),
            inp_idx,
        )
        tag = inp.get("type", "input")
        if tag not in ("input", "textarea"):
            tag = "input"
        target["selector"] = f"{tag}:nth-of-type({position + 1})"
        if label:
            target["text"] = label
        return target, extra

    # --- Priority 4: match_index fallback ---
    if label:
        target["text"] = label
    else:
        target["selector"] = "input"
    extra["match_index"] = inp_idx
    return target, extra


def _detect_intent(desc_lower: str) -> str:
    """Detect test intent from description."""
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return intent
    return "explore"


# -- Input value inference ----------------------------------------------------


_INPUT_TYPE_MAP: dict[str, str] = {
    "email": "test@example.com",
    "password": "Test1234!",
    "tel": "010-1234-5678",
    "search": "test query",
    "number": "1",
    "url": "https://example.com",
}

_LABEL_HINTS: dict[str, str] = {
    "email": "email",
    "e-mail": "email",
    "mail": "email",
    "password": "password",
    "pass": "password",
    "name": "name",
    "nickname": "name",
    "username": "name",
    "phone": "tel",
    "tel": "tel",
    "mobile": "tel",
    "search": "search",
    "address": "address",
    "company": "TestCorp",
}


def _is_ai_available() -> bool:
    """Check if AI adapter is available for parameter extraction."""
    try:
        from aat.adapters import ADAPTER_REGISTRY
        from aat.core.config import load_config

        config = load_config()
        adapter_cls = ADAPTER_REGISTRY.get(config.ai.provider)
        return adapter_cls is not None
    except Exception:
        return False


def _extract_with_ai(description: str, inp: dict[str, Any]) -> str | None:
    """Use LLM to intelligently extract parameter value from description.

    Returns None if extraction fails or AI is unavailable.
    """
    try:
        from aat.adapters import ADAPTER_REGISTRY
        from aat.adapters.prompts import _SYSTEM_EXTRACT_PARAMS
        from aat.core.config import load_config

        config = load_config()
        adapter_cls = ADAPTER_REGISTRY.get(config.ai.provider)
        if not adapter_cls:
            return None

        adapter = adapter_cls(config.ai)

        # Build prompt in OpenAI-compatible format
        input_type = inp.get("input_type", "text")
        input_label = inp.get("label", "text field")
        user_content = f"Description: {description}\nInput type: {input_type}\nInput label: {input_label}"

        messages = [
            {"role": "system", "content": _SYSTEM_EXTRACT_PARAMS},
            {"role": "user", "content": user_content},
        ]

        # Call AI - use existing event loop if available
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # If we're in an async context, we need to handle this differently
        # For now, use run_coroutine_threadsafe or create a new loop
        if loop.is_running():
            # Create a new loop in a thread to avoid conflicts
            import threading

            result = [None]
            exception = [None]

            def run_in_thread():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    # Use _call_json for structured response
                    result[0] = new_loop.run_until_complete(
                        adapter._call_json(messages, max_tokens=2048, temperature=0.3)
                    )
                except Exception as e:
                    exception[0] = e
                finally:
                    new_loop.close()

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join(timeout=30)

            if exception[0]:
                raise exception[0]
            data = result[0]
        else:
            # Use _call_json for structured response
            data = loop.run_until_complete(
                adapter._call_json(messages, max_tokens=2048, temperature=0.3)
            )

        # Extract value with confidence check
        value = data.get("value", "")
        confidence = data.get("confidence", 0.0)

        # Only use high-confidence results
        if value and confidence >= 0.7:
            return value

    except Exception:
        # Silently fall back to heuristics on any error
        pass

    return None


def _infer_input_value(
    inp: dict[str, Any],
    intent: str,
    account: dict[str, str],
    description: str = "",
) -> str:
    """Infer a test value for an input field using AI.

    Strategy: Use LLM to intelligently extract parameters from description.
    Falls back to basic heuristics if AI is unavailable or fails.
    """
    # Smart path: Use AI to extract parameter value
    if _is_ai_available():
        ai_value = _extract_with_ai(description, inp)
        if ai_value:
            return ai_value

    # Fallback: Basic heuristics for common input types
    input_type = (inp.get("input_type") or "").lower()
    if input_type in _INPUT_TYPE_MAP:
        if input_type == "email" and account.get("email"):
            return account["email"]
        if input_type == "password" and account.get("password"):
            return account["password"]
        return _INPUT_TYPE_MAP[input_type]

    # Check selector/label for type hints
    selector = (inp.get("selector") or "").lower()
    label = (inp.get("label") or "").lower()
    role = (inp.get("role") or "").lower()
    combined = f"{selector} {label} {role}"

    # Match by label hints
    for hint_text, field_type in _LABEL_HINTS.items():
        if hint_text in combined:
            if field_type == "email" and account.get("email"):
                return account["email"]
            if field_type == "password" and account.get("password"):
                return account["password"]
            if field_type == "name" and account.get("name"):
                return account["name"]
            return _INPUT_TYPE_MAP.get(field_type, "test input")

    # Match by input type in selector
    for input_type, default_val in _INPUT_TYPE_MAP.items():
        if f'type="{input_type}"' in selector or f"type={input_type}" in selector:
            if input_type == "email" and account.get("email"):
                return account["email"]
            if input_type == "password" and account.get("password"):
                return account["password"]
            return default_val

    # Default for text inputs
    if intent == "search":
        return "test query"
    return "test input"


def _input_description(inp: dict[str, Any]) -> str:
    """Human-readable description of an input field."""
    label = str(inp.get("label", ""))
    if label and len(label) < 30:
        return label
    input_type = str(inp.get("input_type", ""))
    if input_type and input_type != "text":
        return input_type
    selector = str(inp.get("selector", ""))
    if "email" in selector.lower():
        return "email"
    if "password" in selector.lower():
        return "password"
    return "text field"


def _is_submit_button(el: dict[str, Any], intent: str) -> bool:
    """Check if element is a form submit button.

    Supports:
    - DOM elements (via label)
    - Accessibility elements (via accessible_name or role)
    - Flutter Semantics elements (via label)
    """
    # Check both label and accessible_name
    label = (el.get("label") or "").lower()
    accessible_name = (el.get("accessible_name") or "").lower()
    role = (el.get("role") or "").lower()

    # Combine all text sources
    combined_text = f"{label} {accessible_name} {role}"

    submit_words = [
        "login",
        "sign in",
        "submit",
        "register",
        "sign up",
        "confirm",
        "search",
        "create",
        "generate",
        "send",
        "ok",
        "continue",
        # Chinese translations
        "提交",
        "确认",
        "发送",
        "搜索",
        "登录",
        "注册",
    ]
    return any(w in combined_text for w in submit_words)


# -- Flow validation ----------------------------------------------------------


def _validate_form_flow(
    steps: list[dict[str, Any]],
    inputs: list[dict[str, Any]],
    account: dict[str, str],
) -> list[dict[str, Any]]:
    """Validate and fix: ensure inputs are filled before submit."""
    # Check if there are find_and_type steps
    has_type_steps = any(s.get("action") == "find_and_type" for s in steps)

    if not has_type_steps and inputs:
        # Inputs exist but no type steps — add them before first click
        first_click_idx = next(
            (i for i, s in enumerate(steps) if s.get("action") == "find_and_click"),
            len(steps),
        )
        insert_steps: list[dict[str, Any]] = []
        for inp in inputs:
            value = _infer_input_value(inp, "explore", account)
            if not value:
                continue
            target: dict[str, Any] = {}
            if inp.get("selector"):
                target["selector"] = inp["selector"]
            if inp.get("label"):
                target["text"] = inp["label"]
            if not target:
                continue
            insert_steps.append(
                {
                    "step": 0,
                    "action": "find_and_type",
                    "target": target,
                    "value": value,
                    "region": "main",
                    "description": f"Enter {_input_description(inp)}",
                }
            )

        for s in reversed(insert_steps):
            steps.insert(first_click_idx, s)

    return steps


def _next_scenario_id() -> str:
    """Generate next SC-NNN id based on existing scenario files."""
    import glob
    import re

    existing: list[int] = []
    for f in glob.glob("scenarios/SC-*.yaml") + glob.glob("scenarios/SC-*.yml"):
        m = re.search(r"SC-(\d+)", f)
        if m:
            existing.append(int(m.group(1)))
    next_num = max(existing, default=0) + 1
    return f"SC-{next_num:03d}"


def _extract_keywords(description: str) -> list[str]:
    """Extract meaningful keywords from test description."""
    import re

    # Remove common filler words
    fillers = {
        "test",
        "testing",
        "check",
        "verify",
        "the",
        "a",
        "an",
        "and",
        "or",
        "for",
        "with",
        "from",
        "to",
        "by",
        "in",
        "on",
        "at",
        "of",
        "is",
        "then",
        "box",
    }
    # Remove punctuation and split
    cleaned = re.sub(r"[,:;''\"" "()]", " ", description)
    words = cleaned.replace("-", " ").replace("→", " ").split()
    keywords = [
        w.strip() for w in words if w.strip().lower() not in fillers and len(w.strip()) > 1
    ]
    return keywords


def _find_matching_elements(
    keyword: str,
    elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find elements whose label contains the keyword or a synonym.

    Priority order:
    1. accessibility source with role (most reliable - filters decorative elements)
    2. accessibility source with accessible_name
    3. semantics source with role
    4. dom source with semantic selector
    5. other sources
    """
    # Button/action keyword synonyms (include Chinese translations)
    SYNONYMS: dict[str, list[str]] = {
        "send": ["search", "submit", "go", "find", "查询", "搜索"],
        "submit": ["confirm", "save", "apply", "提交", "确认", "发送"],
        "search": ["find", "look", "find", "查询", "搜索", "查找"],
        "click": ["press", "tap", "点击"],
        "ok": ["confirm", "done", "完成", "确定"],
        "cancel": ["close", "dismiss", "取消", "关闭"],
        "next": ["forward", "continue", "继续", "下一步"],
        "back": ["return", "previous", "返回", "后退"],
    }

    kw = keyword.lower()

    # Direct match in label or accessible_name
    matches = [
        el
        for el in elements
        if kw in el.get("label", "").lower() or kw in el.get("accessible_name", "").lower()
    ]

    # If no direct match, try synonyms
    if not matches and kw in SYNONYMS:
        for synonym in SYNONYMS[kw]:
            matches = [
                el
                for el in elements
                if synonym in el.get("label", "").lower()
                or synonym in el.get("accessible_name", "").lower()
            ]
            if matches:
                break

    # Also check selector, role, and type
    if not matches:
        matches = [
            el
            for el in elements
            if kw in el.get("selector", "").lower()
            or kw in el.get("role", "").lower()
            or kw in el.get("input_type", "").lower()
            or kw in el.get("type", "").lower()
        ]

    # Priority: accessibility > semantics > dom > ocr
    source_priority = {
        "accessibility": 0,  # NEW: highest priority (filters decorative)
        "semantics": 1,
        "dom": 2,
        "ocr": 3,
    }

    # Type priority: button/label > input > svg > a
    type_priority = {
        "button": 0,
        "label": 0,
        "textbox": 0,
        "input": 1,
        "accessibility": 1,  # special type marker
        "svg": 2,
        "a": 3,
    }

    matches.sort(
        key=lambda e: (
            source_priority.get(e.get("source", "ocr"), 9),
            type_priority.get(e.get("type", ""), 5),
        )
    )
    return matches


# -- Scenario fixing ----------------------------------------------------------


def _fix_scenario(
    yaml_text: str,
    scan_data: dict[str, Any],
    fail_info: dict[str, Any],
    attempt: int,
) -> str:
    """Fix scenario based on failure info and fresh scan data."""
    import yaml

    try:
        scenario = yaml.safe_load(yaml_text)
    except Exception:
        return yaml_text

    failed_step = fail_info.get("step", 0)
    elements = scan_data.get("elements", [])

    if not scenario or "steps" not in scenario:
        return yaml_text

    for step in scenario["steps"]:
        if step.get("step") != failed_step:
            continue

        target = step.get("target", {})
        text = target.get("text", "")
        if not text:
            continue

        # Try to find updated element in fresh scan
        matches = _find_matching_elements(text, elements)
        if matches:
            best = matches[0]
            target["text"] = best["label"]
            if best.get("selector") and best["source"] == "dom":
                target["selector"] = best["selector"]
            step["description"] += f" # Fixed attempt {attempt}"
        break

    return yaml.safe_dump(
        scenario,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def _read_last_failure(data_dir: Path) -> dict[str, Any]:
    """Read last failure info from skill_attempts or last_run."""
    try:
        last_run = data_dir / "last_run.json"
        if last_run.exists():
            data = json.loads(last_run.read_text("utf-8"))
            results = data.get("results", [])
            for r in results:
                if r.get("status") == "failed":
                    return {
                        "step": int(r.get("step", 0)),
                        "error": r.get("error", ""),
                        "action": r.get("action", ""),
                    }
    except Exception:
        pass
    return {}


# -- Helpers ------------------------------------------------------------------


def _run_aat(args: list[str], env: dict[str, str] | None = None) -> int:
    """Run aat CLI command as subprocess.

    Args:
        args: CLI arguments for aat (e.g. ["run", "--skill-mode", "scenario.yaml"]).
        env: Optional environment variables to pass. Used internally to set
             _AAT_DEVQA_APPROVED=1 after user approves in devqa prompt.
    """
    import shutil

    aat_bin = shutil.which("aat")
    cmd = [aat_bin, *args] if aat_bin else [sys.executable, "-m", "aat", *args]
    result = subprocess.run(cmd, capture_output=False, env=env)
    return result.returncode


def _report_failure(data_dir: Path) -> None:
    """Report failure summary."""
    fail = _read_last_failure(data_dir)
    if fail:
        typer.echo(
            f"[AWT] Last failure: Step {fail.get('step')} — {fail.get('error', 'unknown')[:100]}"
        )
    typer.echo("[AWT] Suggestions:")
    typer.echo("  1. Check .aat/screenshots/ for failure screenshots")
    typer.echo("  2. Run: aat scan --url <url> to re-scan elements")
    typer.echo("  3. Check source code for the failing component")
