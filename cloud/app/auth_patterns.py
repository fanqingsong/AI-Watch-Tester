"""Auth Pattern Detection — registration/login page pattern analysis.

Detects auth page patterns (single_page, multi_step, social_only, captcha, etc.)
and provides crawl strategies, test data generation, and AI prompt context.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registration patterns (10)
# ---------------------------------------------------------------------------

REGISTRATION_PATTERNS: dict[str, dict[str, Any]] = {
    "single_page": {
        "description": "Single-page signup (all fields on one screen)",
        "indicators": ["form with 3+ input fields", "password confirm field"],
        "fields_min": 3,
        "crawl_strategy": "collect_all_fields",
        "testable": True,
    },
    "multi_step": {
        "description": "Multi-step signup (advance via next button)",
        "indicators": ["next/continue button", "step indicator", "progress bar"],
        "next_button_texts": ["next", "Next", "Continue", "proceed"],
        "crawl_strategy": "fill_and_advance",
        "testable": True,
    },
    "social_only": {
        "description": "Social login only (email signup unavailable)",
        "indicators": ["google/kakao/naver/github button only", "no email input"],
        "crawl_strategy": "detect_only",
        "testable": False,
        "limitation": "OAuth only — automated testing not supported",
    },
    "social_plus_email": {
        "description": "Social + email signup both available",
        "indicators": ["social buttons + email input"],
        "crawl_strategy": "collect_all_fields",
        "testable": True,
    },
    "email_verification": {
        "description": "Email verification required (verification code step)",
        "indicators": ["verification code input", "verification code", "verify"],
        "crawl_strategy": "collect_all_fields",
        "testable": "partial",
        "limitation": "Email verification step not automatable — test up to form submit only",
    },
    "invite_only": {
        "description": "Invite code required",
        "indicators": ["invite code input", "invite code", "invitation"],
        "crawl_strategy": "collect_all_fields",
        "testable": "partial",
        "limitation": "Invite code required — test signup flow only without code",
    },
    "phone_otp": {
        "description": "Phone authentication (SMS OTP)",
        "indicators": ["phone input + verify button", "send verification code"],
        "crawl_strategy": "collect_all_fields",
        "testable": "partial",
        "limitation": "SMS verification step not automatable — test up to form submit only",
    },
    "captcha": {
        "description": "Includes CAPTCHA",
        "indicators": ["recaptcha", "hcaptcha", "turnstile", "captcha iframe"],
        "crawl_strategy": "collect_all_fields",
        "testable": False,
        "limitation": "CAPTCHA detected — automated testing not supported",
    },
    "terms_agreement": {
        "description": "Terms agreement required (checkbox)",
        "indicators": ["terms checkbox", "terms of service", "privacy policy"],
        "crawl_strategy": "collect_all_fields",
        "testable": True,
    },
    "modal_registration": {
        "description": "Modal/popup-based signup",
        "indicators": ["modal with form fields after button click"],
        "crawl_strategy": "collect_all_fields",
        "testable": True,
    },
}

# ---------------------------------------------------------------------------
# Login patterns (6)
# ---------------------------------------------------------------------------

LOGIN_PATTERNS: dict[str, dict[str, Any]] = {
    "email_password": {
        "description": "Email + password login",
        "indicators": ["email input + password input + submit"],
        "testable": True,
    },
    "username_password": {
        "description": "Username + password login",
        "indicators": ["text input (id/username) + password input + submit"],
        "testable": True,
    },
    "social_only": {
        "description": "Social login only",
        "indicators": ["social buttons only, no form inputs"],
        "testable": False,
        "limitation": "Social authentication only — automated testing not supported",
    },
    "social_plus_form": {
        "description": "Social + email/username login",
        "indicators": ["social buttons + email/id input"],
        "testable": True,
    },
    "phone_otp": {
        "description": "Phone number OTP login",
        "indicators": ["phone input + send code button"],
        "testable": False,
        "limitation": "SMS verification required — automated testing not supported",
    },
    "passwordless": {
        "description": "Passwordless login (magic link, etc.)",
        "indicators": ["email only, no password field"],
        "testable": False,
        "limitation": "Email magic link method — automated testing not supported",
    },
}


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_auth_pattern(
    fields: list[dict],
    page_html_hints: dict,
    page_type: str = "registration",
) -> dict:
    """Detect auth pattern from form fields and HTML hints.

    Returns {"pattern": "...", "details": {...}, "limitations": [...]}.
    """
    limitations: list[str] = []
    detected: str = ""

    has_email = any(
        f.get("type") == "email"
        or "email" in (f.get("name", "") + f.get("placeholder", "") + f.get("label", "")).lower()
        or "email" in (f.get("placeholder", "") + f.get("label", ""))
        for f in fields
    )
    has_password = any(f.get("type") == "password" for f in fields)
    has_text_input = any(
        f.get("type") in ("text", "search")
        and f.get("tag") != "button"
        for f in fields
    )
    social_buttons = page_html_hints.get("social_buttons", [])
    has_social = bool(social_buttons)
    has_captcha = page_html_hints.get("has_captcha", False)
    has_next_button = page_html_hints.get("has_next_button", False)
    has_terms = page_html_hints.get("has_terms", False)
    has_invite_code = page_html_hints.get("has_invite_code", False)
    has_phone_verify = page_html_hints.get("has_phone_verify", False)

    # Input fields (excluding buttons)
    input_fields = [f for f in fields if f.get("type") != "submit_button"]

    if page_type == "login":
        return _detect_login_pattern(
            has_email=has_email,
            has_password=has_password,
            has_text_input=has_text_input,
            has_social=has_social,
            social_buttons=social_buttons,
            has_captcha=has_captcha,
        )

    # --- Registration detection ---

    # Also check form fields for a "Next" button (supplements HTML hint)
    _next_keywords = {"next", "continue", "proceed"}
    has_next_in_fields = any(
        f.get("type") == "submit_button"
        and f.get("context") == "form"
        and any(kw in (f.get("label") or "").lower() for kw in _next_keywords)
        for f in fields
    )
    if has_next_in_fields:
        has_next_button = True

    # 1) Multi-step (highest priority — "next" button in form context)
    if has_next_button:
        detected = "multi_step"

    # 2) CAPTCHA (additive limitation — does NOT override multi_step)
    if has_captcha:
        pat = REGISTRATION_PATTERNS["captcha"]
        limitations.append(pat["limitation"])
        if not detected:
            detected = "captcha"

    # 3) Social only (no email field)
    if has_social and not has_email and not has_password:
        pat = REGISTRATION_PATTERNS["social_only"]
        limitations.append(pat["limitation"])
        if not detected:
            detected = "social_only"

    # 4) Social + email
    elif has_social and (has_email or has_password):
        if not detected:
            detected = "social_plus_email"

    # 5) Invite code
    if has_invite_code:
        pat = REGISTRATION_PATTERNS["invite_only"]
        limitations.append(pat["limitation"])
        if not detected:
            detected = "invite_only"

    # 6) Phone OTP
    if has_phone_verify:
        pat = REGISTRATION_PATTERNS["phone_otp"]
        limitations.append(pat["limitation"])
        if not detected:
            detected = "phone_otp"

    # 7) Terms agreement (fallback)
    if has_terms and not detected:
        detected = "terms_agreement"

    # 8) Default: single_page
    if not detected:
        detected = "single_page" if len(input_fields) >= 3 else "single_page"

    patterns = REGISTRATION_PATTERNS
    pattern_data = patterns.get(detected, {})

    return {
        "pattern": detected,
        "details": pattern_data,
        "limitations": limitations,
        "page_type": page_type,
        "social_buttons": social_buttons,
        "field_count": len(input_fields),
    }


def _detect_login_pattern(
    *,
    has_email: bool,
    has_password: bool,
    has_text_input: bool,
    has_social: bool,
    social_buttons: list,
    has_captcha: bool,
) -> dict:
    """Detect login page pattern."""
    limitations: list[str] = []
    detected: str = ""

    if has_captcha:
        # Captcha on login page — use registration captcha limitation
        limitations.append(REGISTRATION_PATTERNS["captcha"]["limitation"])

    # Social only (no form inputs)
    if has_social and not has_email and not has_password and not has_text_input:
        detected = "social_only"
        pat = LOGIN_PATTERNS["social_only"]
        limitations.append(pat["limitation"])

    # Social + form
    elif has_social and (has_email or has_password or has_text_input):
        detected = "social_plus_form"

    # Email + password
    elif has_email and has_password:
        detected = "email_password"

    # Username + password (text input, not email)
    elif has_text_input and has_password:
        detected = "username_password"

    # Phone OTP (no password)
    elif has_text_input and not has_password:
        detected = "passwordless"
        pat = LOGIN_PATTERNS["passwordless"]
        limitations.append(pat["limitation"])

    # Fallback
    else:
        detected = "email_password"

    pattern_data = LOGIN_PATTERNS.get(detected, {})

    return {
        "pattern": detected,
        "details": pattern_data,
        "limitations": limitations,
        "page_type": "login",
        "social_buttons": social_buttons,
    }


# ---------------------------------------------------------------------------
# HTML hint collection (runs in browser via page.evaluate)
# ---------------------------------------------------------------------------


async def collect_page_html_hints(page: Any) -> dict:
    """Collect auth-related hints from page HTML via page.evaluate()."""
    return await page.evaluate("""() => {
        const hints = {
            social_buttons: [],
            has_captcha: false,
            has_next_button: false,
            has_terms: false,
            has_invite_code: false,
            has_phone_verify: false,
        };

        // Social buttons: href/class containing provider names
        const socialProviders = [
            'google', 'kakao', 'naver', 'github',
            'facebook', 'apple', 'twitter',
        ];
        document.querySelectorAll('a, button').forEach(el => {
            const href = (el.getAttribute('href') || '').toLowerCase();
            const cls = (typeof el.className === 'string' ? el.className : '').toLowerCase();
            const text = (el.textContent || '').toLowerCase().trim();
            const id = (el.id || '').toLowerCase();
            for (const provider of socialProviders) {
                if (href.includes(provider) || cls.includes(provider)
                    || text.includes(provider) || id.includes(provider)
                    || href.includes('oauth') || href.includes('social')) {
                    hints.social_buttons.push(provider);
                    break;
                }
            }
        });
        hints.social_buttons = [...new Set(hints.social_buttons)];

        // CAPTCHA: only match known CAPTCHA widget selectors
        // Removed overly broad '#captcha' / '.captcha' to avoid false positives
        const captchaSelectors = [
            'iframe[src*="recaptcha"]', 'iframe[src*="hcaptcha"]',
            'iframe[src*="turnstile"]', '.g-recaptcha', '.h-captcha',
            '[data-sitekey]',
        ];
        for (const sel of captchaSelectors) {
            if (document.querySelector(sel)) {
                hints.has_captcha = true;
                break;
            }
        }

        // Next/Continue button
        const nextTexts = ['next', 'continue', 'proceed'];
        document.querySelectorAll('button, input[type="submit"], a.btn, a.button').forEach(el => {
            const text = (el.textContent || el.value || '').trim().toLowerCase();
            if (nextTexts.some(nt => text.includes(nt))) {
                hints.has_next_button = true;
            }
        });

        // Terms checkbox
        const bodyText = document.body ? document.body.innerText.toLowerCase() : '';
        const termsKeywords = [
            ['terms of service', 'privacy policy'],
            'privacy policy', 'terms and conditions',
        ];
        if (document.querySelector('input[type="checkbox"]')) {
            if (termsKeywords.some(kw => bodyText.includes(kw))) {
                hints.has_terms = true;
            }
        }

        // Invite code field
        document.querySelectorAll('input').forEach(el => {
            const ph = (el.placeholder || '').toLowerCase();
            const name = (el.name || '').toLowerCase();
            const label = (el.getAttribute('aria-label') || '').toLowerCase();
            const hint = ph + ' ' + name + ' ' + label;
            if (hint.includes('invite') || hint.includes('invite') || hint.includes('invitation')) {
                hints.has_invite_code = true;
            }
        });

        // Phone verification
        const hasTel = !!document.querySelector('input[type="tel"]');
        if (hasTel) {
            const verifyTexts = ['verify', 'send code', 'otp'];
            document.querySelectorAll('button').forEach(el => {
                const text = (el.textContent || '').trim().toLowerCase();
                if (verifyTexts.some(vt => text.includes(vt))) {
                    hints.has_phone_verify = true;
                }
            });
        }

        return hints;
    }""")


# ---------------------------------------------------------------------------
# Multi-step form crawling
# ---------------------------------------------------------------------------


async def _safe_interact(page: Any, selector: str, value: str) -> bool:
    """Fill/click with fallback to attribute selector for special chars in IDs."""
    for sel in _selector_variants(selector):
        try:
            if value == "__CHECK__":
                await page.click(sel)
            elif value == "__SELECT_FIRST__":
                await page.select_option(sel, index=0)
            else:
                await page.fill(sel, value)
            return True
        except Exception:
            continue
    logger.debug("Failed to interact with %s", selector)
    return False


def _selector_variants(selector: str) -> list[str]:
    """Return selector variants for robustness (original + attribute fallback)."""
    variants = [selector]
    if selector.startswith("#"):
        # Attribute selector fallback for IDs with special characters
        raw_id = selector[1:]
        variants.append(f'[id="{raw_id}"]')
    return variants


async def crawl_multi_step_form(
    page: Any,
    fields: list[dict],
    max_steps: int = 5,
) -> list[list[dict]]:
    """Crawl multi-step form by filling fields and clicking Next.

    Returns list of field lists, one per step.
    SPA/React apps often have dynamic IDs, so we re-collect fresh
    selectors from the live page and use type-based filling as fallback.
    """
    # Re-collect fresh fields from the live page (dynamic IDs may differ
    # from the originally crawled data).
    fresh = await _collect_visible_fields(page)
    input_only = fresh if fresh else [
        f for f in fields if f.get("type") != "submit_button"
    ]
    all_steps: list[list[dict]] = [input_only]
    # Track all seen field signatures for cycle detection
    _seen_signatures: list[frozenset] = [
        frozenset(
            (f.get("name"), f.get("type"), f.get("label"))
            for f in input_only
        ),
    ]
    start_url = page.url
    logger.info(
        "Multi-step crawl starting — step 1 has %d fields, url=%s",
        len(input_only), start_url,
    )

    for _step_num in range(2, max_steps + 1):
        # 1) Fill current fields with test data
        filled = await _fill_fields(page, input_only)
        logger.info(
            "Multi-step crawl — filled %d/%d fields before next",
            filled, len(input_only),
        )

        # 2) Click "Next" button via Playwright (real mouse events
        #    for React/MUI compatibility)
        next_clicked = await _click_next_button(page, fields)
        if not next_clicked:
            logger.info("Multi-step crawl — no next button, stopping")
            break
        await asyncio.sleep(2.0)

        # 3) Check if URL changed (navigation = submitted, not step)
        current_url = page.url
        if current_url != start_url:
            logger.info(
                "Multi-step crawl — URL changed %s → %s, stopping",
                start_url, current_url,
            )
            break

        # 4) Collect new fields
        new_fields = await _collect_visible_fields(page)
        logger.info(
            "Multi-step crawl step %d — collected %d fields",
            _step_num, len(new_fields) if new_fields else 0,
        )
        if not new_fields:
            break
        # Compare by field names/types to detect real changes
        new_keys = frozenset(
            (f.get("name"), f.get("type"), f.get("label"))
            for f in new_fields
        )
        old_keys = _seen_signatures[-1]
        if old_keys == new_keys:
            logger.info(
                "Multi-step crawl step %d — same fields, stopping",
                _step_num,
            )
            break
        # Cycle detection: stop if we've seen this field set before
        if new_keys in _seen_signatures:
            logger.info(
                "Multi-step crawl step %d — cycle detected, stopping",
                _step_num,
            )
            break
        _seen_signatures.append(new_keys)
        all_steps.append(new_fields)
        input_only = new_fields

    return all_steps


async def _fill_fields(page: Any, fields: list[dict]) -> int:
    """Fill form fields using CSS selector with type-based fallback."""
    filled = 0
    # Track type-based fill indices for fallback
    type_indices: dict[str, int] = {}

    for field in fields:
        value = generate_test_data(field)
        if not value:
            continue
        selector = field.get("selector")

        # Try CSS selector first
        if selector:
            ok = await _safe_interact(page, selector, value)
            if ok:
                filled += 1
                continue

        # Fallback: fill by input type + index
        ftype = field.get("type", "text")
        idx = type_indices.get(ftype, 0)
        type_indices[ftype] = idx + 1
        try:
            loc = page.locator(f'input[type="{ftype}"]').nth(idx)
            if await loc.count() > 0:
                if value == "__CHECK__":
                    await loc.click(timeout=3000)
                else:
                    await loc.fill(value, timeout=3000)
                filled += 1
        except Exception:
            logger.debug("Type-based fill failed: %s[%d]", ftype, idx)

    return filled


async def _click_next_button(
    page: Any, fields: list[dict] | None = None,
) -> bool:
    """Find and click a Next/Continue button.

    Uses Playwright's page.click() instead of JS b.click() for
    better compatibility with React/MUI synthetic events.
    """
    _next_kw = ["next", "continue", "proceed"]

    # 1) Find the next button via JS, return its index for page.click()
    btn_index = await page.evaluate("""(nextTexts) => {
        const buttons = document.querySelectorAll('button, input[type="submit"]');
        for (let i = 0; i < buttons.length; i++) {
            const b = buttons[i];
            const text = (b.textContent || b.value || '').trim().toLowerCase();
            if (nextTexts.some(nt => text.includes(nt))
                && b.offsetParent !== null) {
                return i;
            }
        }
        return -1;
    }""", _next_kw)

    if btn_index >= 0:
        try:
            loc = page.locator(
                'button, input[type="submit"]',
            ).nth(btn_index)
            await loc.click(timeout=5000)
            return True
        except Exception:
            logger.debug("Playwright click on next[%d] failed", btn_index)

    # 2) Fallback: try form submit button with next-like text only
    for kw in _next_kw:
        try:
            loc = page.locator('button[type="submit"]').filter(has_text=kw).first
            if await loc.count() > 0:
                await loc.click(timeout=5000)
                return True
        except Exception:
            continue

    # 3) Fallback: use selector from crawled fields
    if fields:
        for f in fields:
            if f.get("type") == "submit_button" and f.get("selector"):
                lbl = (f.get("label") or "").lower()
                if any(kw in lbl for kw in _next_kw):
                    try:
                        await page.click(f["selector"], timeout=3000)
                        return True
                    except Exception:
                        logger.debug(
                            "Field-based click failed: %s", f["selector"],
                        )

    # 4) Fallback: Playwright semantic locator (get_by_text / get_by_role)
    for kw in _next_kw:
        try:
            loc = page.get_by_role("button", name=kw)
            if await loc.count() > 0:
                await loc.first.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


async def _collect_visible_fields(page: Any) -> list[dict]:
    """Collect currently visible form fields + buttons from the page."""
    return await page.evaluate("""() => {
        const fields = [];
        document.querySelectorAll('input, textarea, select').forEach(f => {
            if (f.type === 'hidden') return;
            if (f.offsetParent === null && f.offsetWidth === 0) return;
            const labelEl = f.id
                ? document.querySelector('label[for="' + f.id + '"]')
                : null;
            const parentLabel = !labelEl ? f.closest('label') : null;
            const labelNode = labelEl || parentLabel;
            const label = labelNode
                ? (labelNode.childNodes[0]?.textContent?.trim()
                   || labelNode.textContent?.trim()?.substring(0, 100))
                : '';
            // Use CSS.escape for IDs with special characters (e.g. «rf»)
            let sel = null;
            if (f.id) sel = '#' + CSS.escape(f.id);
            else if (f.name) sel = f.tagName.toLowerCase()
                + '[name="' + CSS.escape(f.name) + '"]';
            else if (f.type && f.type !== 'text')
                sel = f.tagName.toLowerCase()
                + '[type="' + f.type + '"]';
            fields.push({
                tag: f.tagName.toLowerCase(),
                type: f.type || 'text',
                name: f.name || '',
                placeholder: f.placeholder || '',
                label: label || '',
                aria_label: f.getAttribute('aria-label') || '',
                selector: sel,
                required: f.required || false,
            });
        });
        // Also collect visible buttons (submit/next/complete)
        document.querySelectorAll(
            'button, input[type="submit"]'
        ).forEach(b => {
            if (b.offsetParent === null && b.offsetWidth === 0) return;
            const text = (b.textContent || b.value || '').trim();
            if (!text) return;
            let sel = null;
            if (b.id) sel = '#' + CSS.escape(b.id);
            else sel = 'button';
            fields.push({
                tag: b.tagName.toLowerCase(),
                type: 'submit_button',
                name: b.name || '',
                placeholder: '',
                label: text.substring(0, 100),
                aria_label: b.getAttribute('aria-label') || '',
                selector: sel,
                required: false,
            });
        });
        return fields;
    }""")


# ---------------------------------------------------------------------------
# Test data generation
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    """Generate a unique test email with timestamp suffix."""
    import time

    ts = int(time.time()) % 100000
    return f"awttest_{ts}@example.com"


def generate_test_data(field: dict) -> str | None:
    """Generate dummy test data appropriate for the field type."""
    f_type = field.get("type", "text")
    ph = field.get("placeholder", "").lower()
    label = field.get("label", "").lower()
    name = field.get("name", "").lower()
    hint = f"{ph} {label} {name}"

    if f_type == "email" or "email" in hint or "email" in hint:
        return _unique_email()
    if f_type == "password" or "password" in hint or "password" in hint:
        return "TestPass123!"
    if f_type == "tel" or "phone" in hint or "phone" in hint or "mobile" in hint:
        return "01012345678"
    if "name" in hint or "name" in hint:
        return "Test User"
    if f_type == "checkbox":
        return "__CHECK__"
    if f_type == "select":
        return "__SELECT_FIRST__"
    if f_type in ("text", "search"):
        return "test input"
    return None


# ---------------------------------------------------------------------------
# AI prompt context builder
# ---------------------------------------------------------------------------


def build_auth_context_for_ai(auth_info: dict) -> str:
    """Build auth pattern context string for AI prompt injection."""
    parts: list[str] = []
    pattern = auth_info.get("pattern", "unknown")
    pattern_data = REGISTRATION_PATTERNS.get(pattern) or LOGIN_PATTERNS.get(pattern)

    if pattern_data:
        parts.append(f"AUTH PATTERN: {pattern} — {pattern_data['description']}")

    limitations = auth_info.get("limitations", [])
    if limitations:
        parts.append("LIMITATIONS (honest reporting):")
        for lim in limitations:
            parts.append(f"  - {lim}")
        parts.append("→ SKIP non-testable items and specify reason in description")

    steps_data = auth_info.get("multi_step_fields")
    if steps_data and len(steps_data) > 1:
        # Find the last step's submit button text (skip back/previous buttons)
        _back_kw = ("previous", "back", "prev")
        last_step = steps_data[-1]
        last_btn_text = ""
        for f in last_step:
            if f.get("type") != "submit_button":
                continue
            lbl = (f.get("label") or "").strip().lower()
            if any(kw in lbl for kw in _back_kw):
                continue
            last_btn_text = f.get("label", "")
            break

        parts.append(
            f"MULTI-STEP FORM: {len(steps_data)} steps detected
"
            "→ Signup scenarios must include all steps\.
"
            "→ Insert 'next' button click + wait steps between each stage\.
"
            "→ Insert final submit button click + assert at last stage\.
"
            "→ Skip optional file uploads (profile photo, etc.)\.
\n"
            "→ Test required file uploads with dummy file\.
\n"
            "→ Optional text fields can be skipped\.
\n"
            "STEP ORDER RULE (must comply):
\n"
            "→ Place each field exactly in the collected step (Step N)\.
\n"
            "→ Step 1 fields before 'next' click, Step 2 fields after 'next' click\.
\n"
            "→ Do not move fields to different steps\.
\n"
            "CHECKBOX RULE:\n"
            "→ "agree", "terms", "privacy" text "
            "checkboxes are always required\.
\n"
            "→ Include these checkboxes as find_and_click steps\.
\n"
            "→ Place checkboxes in the collected step (do not move to other step)\.
\n"
            "SUBMIT BUTTON RULE:\n"
            "→ Last stage submit button should use actual button text from collected fields "
            "(use this exact text)
"
        )
        if last_btn_text:
            parts.append(
                f"→ Final submit button: \"{last_btn_text}\" "
                "(use this exact text)"
            )

        for i, step_fields in enumerate(steps_data, 1):
            field_lines = []
            for f in step_fields:
                label = (
                    f.get("label") or f.get("placeholder")
                    or f.get("name") or f.get("type")
                )
                ftype = f.get("type", "text")
                req = f.get("required", False)
                # Agreement checkboxes → force required
                _agree_kw = ("agree", "terms", "privacy")
                if ftype == "checkbox" and any(
                    kw in (label or "").lower() for kw in _agree_kw
                ):
                    req = True
                sel = f.get("selector", "")
                tag = "required" if req else "optional"
                field_lines.append(
                    f"    - {label} (type={ftype}, {tag})"
                    + (f" [selector: {sel}]" if sel else "")
                )
            parts.append(f"  Step {i}:")
            parts.extend(field_lines)

    return "\n".join(parts) if parts else ""
