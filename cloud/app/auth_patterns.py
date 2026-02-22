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
        "description": "단일 페이지 회원가입 (모든 필드가 한 화면에)",
        "indicators": ["form with 3+ input fields", "password confirm field"],
        "fields_min": 3,
        "crawl_strategy": "collect_all_fields",
        "testable": True,
    },
    "multi_step": {
        "description": "멀티스텝 회원가입 (다음 버튼으로 단계 진행)",
        "indicators": ["next/continue button", "step indicator", "progress bar"],
        "next_button_texts": ["다음", "Next", "Continue", "계속", "진행"],
        "crawl_strategy": "fill_and_advance",
        "testable": True,
    },
    "social_only": {
        "description": "소셜 로그인만 가능 (이메일 가입 불가)",
        "indicators": ["google/kakao/naver/github button only", "no email input"],
        "crawl_strategy": "detect_only",
        "testable": False,
        "limitation": "소셜 인증(OAuth)만 지원 — 자동 테스트 불가",
    },
    "social_plus_email": {
        "description": "소셜 + 이메일 가입 모두 가능",
        "indicators": ["social buttons + email input"],
        "crawl_strategy": "collect_all_fields",
        "testable": True,
    },
    "email_verification": {
        "description": "이메일 인증 필요 (인증코드 입력 단계)",
        "indicators": ["verification code input", "인증번호", "verify"],
        "crawl_strategy": "collect_all_fields",
        "testable": "partial",
        "limitation": "이메일 인증 단계는 자동 테스트 불가 — 폼 제출까지만 테스트",
    },
    "invite_only": {
        "description": "초대 코드 필요",
        "indicators": ["invite code input", "초대 코드", "invitation"],
        "crawl_strategy": "collect_all_fields",
        "testable": "partial",
        "limitation": "초대 코드가 필요 — 코드 없이 가입 흐름만 테스트",
    },
    "phone_otp": {
        "description": "휴대폰 인증 (SMS OTP)",
        "indicators": ["phone input + verify button", "인증번호 발송"],
        "crawl_strategy": "collect_all_fields",
        "testable": "partial",
        "limitation": "SMS 인증 단계는 자동 테스트 불가 — 폼 제출까지만 테스트",
    },
    "captcha": {
        "description": "CAPTCHA 포함",
        "indicators": ["recaptcha", "hcaptcha", "turnstile", "captcha iframe"],
        "crawl_strategy": "collect_all_fields",
        "testable": False,
        "limitation": "CAPTCHA 감지 — 자동 테스트 불가",
    },
    "terms_agreement": {
        "description": "약관 동의 필수 (체크박스)",
        "indicators": ["terms checkbox", "이용약관", "개인정보"],
        "crawl_strategy": "collect_all_fields",
        "testable": True,
    },
    "modal_registration": {
        "description": "모달/팝업 기반 가입",
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
        "description": "이메일 + 비밀번호 로그인",
        "indicators": ["email input + password input + submit"],
        "testable": True,
    },
    "username_password": {
        "description": "아이디 + 비밀번호 로그인",
        "indicators": ["text input (id/username) + password input + submit"],
        "testable": True,
    },
    "social_only": {
        "description": "소셜 로그인만 가능",
        "indicators": ["social buttons only, no form inputs"],
        "testable": False,
        "limitation": "소셜 인증만 지원 — 자동 테스트 불가",
    },
    "social_plus_form": {
        "description": "소셜 + 이메일/아이디 로그인",
        "indicators": ["social buttons + email/id input"],
        "testable": True,
    },
    "phone_otp": {
        "description": "전화번호 OTP 로그인",
        "indicators": ["phone input + send code button"],
        "testable": False,
        "limitation": "SMS 인증 필요 — 자동 테스트 불가",
    },
    "passwordless": {
        "description": "비밀번호 없는 로그인 (매직링크 등)",
        "indicators": ["email only, no password field"],
        "testable": False,
        "limitation": "이메일 매직링크 방식 — 자동 테스트 불가",
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
        or "이메일" in (f.get("placeholder", "") + f.get("label", ""))
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
    _next_keywords = {"다음", "next", "continue", "계속", "진행"}
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
        const nextTexts = ['다음', 'next', 'continue', '계속', '진행'];
        document.querySelectorAll('button, input[type="submit"], a.btn, a.button').forEach(el => {
            const text = (el.textContent || el.value || '').trim().toLowerCase();
            if (nextTexts.some(nt => text.includes(nt))) {
                hints.has_next_button = true;
            }
        });

        // Terms checkbox
        const bodyText = document.body ? document.body.innerText.toLowerCase() : '';
        const termsKeywords = [
            '이용약관', '개인정보', 'terms of service',
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
            if (hint.includes('초대') || hint.includes('invite') || hint.includes('invitation')) {
                hints.has_invite_code = true;
            }
        });

        // Phone verification
        const hasTel = !!document.querySelector('input[type="tel"]');
        if (hasTel) {
            const verifyTexts = ['인증', 'verify', '발송', 'send code', 'otp'];
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
        old_keys = {
            (f.get("name"), f.get("type"), f.get("label"))
            for f in input_only
        }
        new_keys = {
            (f.get("name"), f.get("type"), f.get("label"))
            for f in new_fields
        }
        if old_keys == new_keys:
            logger.info(
                "Multi-step crawl step %d — same fields, stopping",
                _step_num,
            )
            break
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
    _next_kw = ["다음", "next", "continue", "계속", "진행"]

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

    # 2) Fallback: try form submit button (type="submit")
    try:
        submit = page.locator('button[type="submit"]').first
        if await submit.count() > 0:
            await submit.click(timeout=5000)
            return True
    except Exception:
        pass

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


def generate_test_data(field: dict) -> str | None:
    """Generate dummy test data appropriate for the field type."""
    f_type = field.get("type", "text")
    ph = field.get("placeholder", "").lower()
    label = field.get("label", "").lower()
    name = field.get("name", "").lower()
    hint = f"{ph} {label} {name}"

    if f_type == "email" or "email" in hint or "이메일" in hint:
        return "awttest@example.com"
    if f_type == "password" or "password" in hint or "비밀번호" in hint:
        return "TestPass123!"
    if f_type == "tel" or "phone" in hint or "전화" in hint or "휴대" in hint:
        return "01012345678"
    if "이름" in hint or "name" in hint:
        return "테스트유저"
    if f_type == "checkbox":
        return "__CHECK__"
    if f_type == "select":
        return "__SELECT_FIRST__"
    if f_type in ("text", "search"):
        return "테스트 입력"
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
        parts.append("LIMITATIONS (정직하게 리포트):")
        for lim in limitations:
            parts.append(f"  - {lim}")
        parts.append("→ 테스트 불가 항목은 SKIP하고 사유를 description에 명시할 것")

    steps_data = auth_info.get("multi_step_fields")
    if steps_data and len(steps_data) > 1:
        # Find the last step's submit button text
        last_step = steps_data[-1]
        last_btn_text = ""
        for f in last_step:
            if f.get("type") == "submit_button":
                last_btn_text = f.get("label", "")
                break

        parts.append(
            f"MULTI-STEP FORM: {len(steps_data)} 단계 감지됨\n"
            "→ 회원가입 시나리오는 반드시 모든 단계를 포함해야 합니다.\n"
            "→ 각 단계 사이에 '다음'/'Next' 버튼 클릭 + wait 스텝을 넣으세요.\n"
            "→ 마지막 단계에서 최종 제출 버튼 클릭 + assert를 넣으세요.\n"
            "→ 선택(optional) 파일 업로드(프로필 사진 등)는 스킵.\n"
            "→ 필수(required) 파일 업로드는 더미 파일로 테스트.\n"
            "→ 선택(optional) 텍스트 필드는 스킵해도 됩니다.\n"
            "STEP ORDER RULE (반드시 준수):\n"
            "→ 각 필드는 아래 수집된 단계(Step N)에 정확히 맞게 배치할 것.\n"
            "→ Step 1 필드는 '다음' 클릭 전에, Step 2 필드는 '다음' 클릭 후에.\n"
            "→ 필드를 다른 단계로 이동하지 마세요.\n"
            "CHECKBOX RULE:\n"
            "→ '동의', 'agree', '약관', 'terms', 'privacy' 텍스트가 "
            "포함된 체크박스는 항상 필수로 처리할 것.\n"
            "→ 이 체크박스들은 반드시 find_and_click 스텝으로 포함하세요.\n"
            "→ 체크박스가 수집된 단계에 배치하세요 (다른 단계로 옮기지 말 것).\n"
            "SUBMIT BUTTON RULE:\n"
            "→ 마지막 단계의 제출 버튼은 수집된 필드의 실제 버튼 텍스트를 "
            "사용할 것."
        )
        if last_btn_text:
            parts.append(
                f"→ 마지막 단계 제출 버튼: \"{last_btn_text}\" "
                "(이 텍스트를 정확히 사용하세요)"
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
                _agree_kw = ("동의", "agree", "약관", "terms", "privacy")
                if ftype == "checkbox" and any(
                    kw in (label or "").lower() for kw in _agree_kw
                ):
                    req = True
                sel = f.get("selector", "")
                tag = "필수" if req else "선택"
                field_lines.append(
                    f"    - {label} (type={ftype}, {tag})"
                    + (f" [selector: {sel}]" if sel else "")
                )
            parts.append(f"  Step {i}:")
            parts.extend(field_lines)

    return "\n".join(parts) if parts else ""
