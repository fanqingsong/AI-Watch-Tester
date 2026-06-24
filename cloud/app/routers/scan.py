"""Smart Scan endpoints — site crawling, AI test plan, execution."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.crawler import crawl_site, get_scan_limits
from app.database import get_db
from app.models import Scan, ScanStatus, ScenarioCache, User
from app.scan_diff import compute_scan_fingerprint, compute_structure_fingerprint, compute_tests_hash
from app.scenario_utils import (
    DEFAULT_AI_MODELS as _DEFAULT_MODELS,
)
from app.scenario_utils import (
    build_language_instruction,
    compress_crawl_data,
    compress_observations_for_ai,
    detect_site_language,
    enforce_multi_step_order,
    ensure_post_submit_assert,
    fix_assert_steps,
    fix_field_targets,
    fix_form_submit_steps,
    inject_login_prefix,
    parse_json,
    validate_and_retry,
    validate_asserts,
)
from app.schemas import (
    ScanExecuteRequest,
    ScanPlanRequest,
    ScanPlanResponse,
    ScanRequest,
    ScanResponse,
    ScanSummary,
)
from app.test_patterns import (
    build_pattern_summary,
    build_pattern_tests,
    match_elements_to_patterns,
)
from app.ws import ws_manager

router = APIRouter(prefix="/api/scan", tags=["scan"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Business test templates — site-type-specific test suggestions
# ---------------------------------------------------------------------------

BUSINESS_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "ecommerce": [
        {
            "requires_feature": "product_list",
            "name_en": "Product Browsing",
            "desc_en": "Browse product listings, verify product details load correctly",
            "priority": "high",
            "estimated_time": 30,
            "requires_auth": False,
        },
        {
            "requires_feature": "cart",
            "name_en": "Add to Cart Flow",
            "desc_en": "Add a product to cart, verify cart count updates and cart page shows item",
            "priority": "high",
            "estimated_time": 40,
            "requires_auth": False,
        },
        {
            "requires_feature": "filter_sort",
            "name_en": "Filter and Sort Products",
            "desc_en": "Apply filters and sorting options, verify product list updates accordingly",
            "priority": "medium",
            "estimated_time": 30,
            "requires_auth": False,
        },
        {
            "requires_feature": "search",
            "name_en": "Product Search",
            "desc_en": "Search for products and verify search results are relevant",
            "priority": "medium",
            "estimated_time": 20,
            "requires_auth": False,
        },
        {
            "requires_feature": "review_form",
            "name_en": "Write Product Review",
            "desc_en": "Write a product review with rating, verify it appears in review list",
            "priority": "medium",
            "estimated_time": 40,
            "requires_auth": True,
            "auth_fields": [
                {"key": "email", "label": "Email", "type": "email", "required": True},
                {"key": "password", "label": "Password", "type": "password", "required": True}],
        }],
    "blog": [
        {
            "requires_feature": "blog",
            "name_en": "Blog Post Navigation",
            "desc_en": "Browse blog posts, click into articles, verify content loads",
            "priority": "high",
            "estimated_time": 25,
            "requires_auth": False,
        },
        {
            "requires_feature": "comment_form",
            "name_en": "Blog Comment",
            "desc_en": "Write a comment on a blog post, verify it appears",
            "priority": "medium",
            "estimated_time": 30,
            "requires_auth": True,
            "auth_fields": [
                {"key": "email", "label": "Email", "type": "email", "required": True},
                {"key": "password", "label": "Password", "type": "password", "required": True}],
        }],
    "community": [
        {
            "requires_feature": "board_write",
            "name_en": "Create Post",
            "desc_en": "Create a new board post with title and content, verify it appears in list",
            "priority": "high",
            "estimated_time": 40,
            "requires_auth": True,
            "auth_fields": [
                {"key": "email", "label": "Email", "type": "email", "required": True},
                {"key": "password", "label": "Password", "type": "password", "required": True}],
        },
        {
            "requires_feature": "comment_form",
            "name_en": "Post Comment",
            "desc_en": "Write a comment on a post, verify it appears",
            "priority": "medium",
            "estimated_time": 30,
            "requires_auth": True,
            "auth_fields": [
                {"key": "email", "label": "Email", "type": "email", "required": True},
                {"key": "password", "label": "Password", "type": "password", "required": True}],
        }],
    "saas": [
        {
            "requires_feature": "login_form",
            "name_en": "Login and Dashboard Access",
            "desc_en": "Login with credentials and verify dashboard loads correctly",
            "priority": "high",
            "estimated_time": 30,
            "requires_auth": True,
            "auth_fields": [
                {"key": "email", "label": "Email", "type": "email", "required": True},
                {"key": "password", "label": "Password", "type": "password", "required": True}],
        },
        {
            "requires_feature": "signup",
            "name_en": "Signup Flow",
            "desc_en": "Complete signup form and verify account creation flow",
            "priority": "high",
            "estimated_time": 40,
            "requires_auth": False,
            "test_data_fields": [
                {
                    "key": "signup_email",
                    "label": "Test Email",
                    "placeholder": "test@example.com",
                    "required": True,
                },
                {
                    "key": "signup_password",
                    "label": "Test Password",
                    "placeholder": "TestPass123!",
                    "required": True,
                }],
        },
        {
            "requires_feature": "search",
            "name_en": "Search Functionality",
            "desc_en": "Use search feature and verify results are displayed",
            "priority": "medium",
            "estimated_time": 20,
            "requires_auth": False,
        }],
    "corporate": [
        {
            "requires_feature": "newsletter",
            "name_en": "Newsletter Subscription",
            "desc_en": "Subscribe to newsletter with email, verify confirmation",
            "priority": "medium",
            "estimated_time": 20,
            "requires_auth": False,
            "test_data_fields": [
                {
                    "key": "newsletter_email",
                    "label": "Test Email",
                    "placeholder": "test@example.com",
                    "required": True,
                }],
        }],
    "portfolio": [],
    "multilingual": [
        {
            "requires_feature": "multilingual",
            "name_en": "Language Switch Test",
            "desc_en": (
                "Switch site language and verify page content changes"
                " accordingly without broken layout"
            ),
            "priority": "medium",
            "estimated_time": 30,
            "requires_auth": False,
        }],
}


# ---------------------------------------------------------------------------
# Feature → Required test mapping (post-plan validation)
# If a feature is detected, the corresponding test MUST exist in the plan.
# AI may miss these; this code-level check force-adds them.
# ---------------------------------------------------------------------------

_FEATURE_REQUIRED_TESTS: list[dict[str, Any]] = [
    {
        "feature": "login_form",
        "keywords": ["login", "sign in", "authentication"],
        "test": {
            "name_en": "Login Test",
            "desc_en": "Enter credentials on login page and verify successful authentication",
            "priority": "high",
            "estimated_time": 30,
            "requires_auth": True,
            "auth_fields": [
                {"key": "email", "label": "Email", "type": "email", "required": True},
                {"key": "password", "label": "Password", "type": "password", "required": True}],
        },
    },
    {
        "feature": "signup",
        "keywords": ["signup", "sign up", "register"],
        "test": {
            "name_en": "Signup Flow Test",
            "desc_en": "Complete signup form and verify account creation flow",
            "priority": "high",
            "estimated_time": 40,
            "requires_auth": False,
            "test_data_fields": [
                {"key": "signup_email", "label": "Test Email",
                 "placeholder": "test@example.com", "required": True},
                {"key": "signup_password", "label": "Test Password",
                 "placeholder": "TestPass123!", "required": True}],
        },
    },
    {
        "feature": "admin_panel",
        "keywords": ["admin", "manage"],
        "test": {
            "name_en": "Admin Panel Access Test",
            "desc_en": "Verify admin panel access and permission checks",
            "priority": "medium",
            "estimated_time": 20,
            "requires_auth": True,
            "auth_fields": [
                {"key": "admin_id", "label": "Admin ID", "type": "text", "required": True},
                {"key": "admin_pw", "label": "Admin Password",
                 "type": "password", "required": True}],
        },
    },
    {
        "feature": "search",
        "keywords": ["search"],
        "test": {
            "name_en": "Search Functionality Test",
            "desc_en": "Enter search query and verify results are displayed",
            "priority": "medium",
            "estimated_time": 20,
            "requires_auth": False,
        },
    },
    {
        "feature": "cart",
        "keywords": ["cart", "basket"],
        "test": {
            "name_en": "Cart Flow Test",
            "desc_en": "Add product to cart and verify cart page shows item",
            "priority": "high",
            "estimated_time": 40,
            "requires_auth": False,
        },
    }]


def _validate_plan_against_features(
    plan: dict[str, Any],
    features: list[str],
    language: str,
) -> dict[str, Any]:
    """Validate plan has tests for all detected features. Force-add if missing."""
    ko = language.lower() in ("ko", "korean")
    categories = plan.get("categories", [])
    feature_set = set(features)

    # Collect all existing test names (lowercase) across all categories
    existing_names: set[str] = set()
    for cat in categories:
        for t in cat.get("tests", []):
            existing_names.add((t.get("name") or "").lower())

    # Find max test ID across all categories
    max_tid = 0
    for cat in categories:
        for t in cat.get("tests", []):
            tid_str = t.get("id", "")
            num = "".join(c for c in tid_str if c.isdigit())
            if num:
                max_tid = max(max_tid, int(num))

    added_tests: list[dict[str, Any]] = []
    next_tid = max_tid + 1

    for mapping in _FEATURE_REQUIRED_TESTS:
        feat = mapping["feature"]
        if feat not in feature_set:
            continue

        # Check if any existing test name contains a keyword
        keywords = mapping["keywords"]
        already_covered = any(
            kw in name for kw in keywords for name in existing_names
        )
        if already_covered:
            continue

        # Force-add this test
        tmpl = mapping["test"]
        test_entry: dict[str, Any] = {
            "id": f"t{next_tid}",
            "name": tmpl["name_ko"] if ko else tmpl["name_en"],
            "description": tmpl["desc_ko"] if ko else tmpl["desc_en"],
            "priority": tmpl.get("priority", "medium"),
            "estimated_time": tmpl.get("estimated_time", 30),
            "requires_auth": tmpl.get("requires_auth", False),
            "selected": not tmpl.get("requires_auth", False),
        }
        if tmpl.get("auth_fields"):
            test_entry["auth_fields"] = tmpl["auth_fields"]
        if tmpl.get("test_data_fields"):
            test_entry["test_data_fields"] = tmpl["test_data_fields"]
        added_tests.append(test_entry)
        next_tid += 1
        logger.info(
            "Plan validation: force-added '%s' for detected feature '%s'",
            test_entry["name"], feat,
        )

    if added_tests:
        # Find or create "business" category
        biz_cat = None
        for cat in categories:
            if cat.get("id") == "business":
                biz_cat = cat
                break
        if biz_cat is None:
            biz_cat = {
                "id": "business",
                "name": "Business Flows" if ko else "Business Flows",
                "auto_selected": False,
                "tests": [],
            }
            categories.append(biz_cat)
        biz_cat["tests"].extend(added_tests)

    plan["categories"] = categories
    return plan


def _dedup_section_nav_tests(plan: dict[str, Any]) -> dict[str, Any]:
    """Remove section navigation tests that duplicate the nav menu test.

    AI sometimes generates tests like "section navigation" or "navigate to About page"
    which are already covered by the nav_menu_test in the basic category.
    """
    nav_dedup_keywords = [
        "section navigation", "section move", "section check", "page move",
        "section navigation", "section nav", "navigate to section"]

    # Check if nav menu test exists in basic category
    has_nav_test = False
    for cat in plan.get("categories", []):
        if cat.get("id") == "basic":
            for t in cat.get("tests", []):
                name_lower = (t.get("name") or "").lower()
                if "navigation menu" in name_lower or "navigation menu" in name_lower:
                    has_nav_test = True
                    break
            break

    if not has_nav_test:
        return plan

    for cat in plan.get("categories", []):
        original_count = len(cat.get("tests", []))
        cat["tests"] = [
            t for t in cat.get("tests", [])
            if not any(
                kw in (t.get("name") or "").lower()
                for kw in nav_dedup_keywords
            )
        ]
        removed = original_count - len(cat["tests"])
        if removed:
            logger.info(
                "Dedup: removed %d section nav test(s) from category '%s'",
                removed, cat.get("name"),
            )

    # Remove empty categories
    plan["categories"] = [
        c for c in plan.get("categories", []) if c.get("tests")
    ]
    return plan


_parse_json = parse_json  # alias for internal usage


def _scan_to_response(scan: Scan) -> dict:
    """Convert Scan ORM to response dict."""
    summary = _parse_json(scan.summary_json)
    return {
        "id": scan.id,
        "target_url": scan.target_url,
        "status": scan.status,
        "summary": ScanSummary(**summary) if summary else None,
        "pages": _parse_json(scan.pages_json),
        "broken_links": _parse_json(scan.broken_links_json),
        "detected_features": _parse_json(scan.detected_features) or [],
        "observations": _parse_json(getattr(scan, "observations_json", None)) or [],
        "logs": _parse_json(getattr(scan, "logs_json", None)) or [],
        "error_message": scan.error_message,
        "created_at": scan.created_at,
        "completed_at": scan.completed_at,
    }


# ---------------------------------------------------------------------------
# POST /api/scan — start crawling
# ---------------------------------------------------------------------------


@router.post("", response_model=ScanResponse, status_code=201)
async def start_scan(
    body: ScanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a smart scan on the target URL."""
    # Apply tier limits
    tier_limits = get_scan_limits(user.tier.value)
    max_pages = min(body.max_pages, tier_limits["max_pages"])
    max_depth = min(body.max_depth, tier_limits["max_depth"])

    scan = Scan(
        user_id=user.id,
        target_url=str(body.target_url),
        status=ScanStatus.SCANNING,
        max_pages=max_pages,
        max_depth=max_depth,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    scan_id = scan.id

    # Run crawl in background
    async def _run_crawl() -> None:
        # Wrap WSManager to collect scan_log messages for persistence
        collected_logs: list[dict[str, Any]] = []

        class _LogCollectingWS:
            """Proxy that intercepts scan_log broadcasts."""

            async def broadcast(self, sid: int, msg: dict) -> None:
                await ws_manager.broadcast(sid, msg)
                if msg.get("type") == "scan_log":
                    collected_logs.append({
                        "phase": msg.get("phase", ""),
                        "message": msg.get("message", ""),
                        "level": msg.get("level"),
                    })

        try:
            result = await crawl_site(
                str(body.target_url),
                scan_id,
                max_pages=max_pages,
                max_depth=max_depth,
                total_timeout=float(tier_limits["timeout"]),
                screenshot_limit=tier_limits["screenshots"],
                ws=_LogCollectingWS(),
                lang="en",
            )

            # Update DB with results FIRST, then broadcast
            from app.database import async_session

            async with async_session() as session:
                s = (await session.execute(
                    select(Scan).where(Scan.id == scan_id)
                )).scalar_one()

                if "error" in result:
                    s.status = ScanStatus.FAILED
                    s.error_message = result["error"]
                else:
                    s.status = ScanStatus.COMPLETED
                    s.summary_json = json.dumps(result["summary"])
                    s.pages_json = json.dumps(result["pages"])
                    s.broken_links_json = json.dumps(result["broken_links"])
                    s.detected_features = json.dumps(result["detected_features"])
                    # Store observations if available
                    if result.get("observations"):
                        s.observations_json = json.dumps(result["observations"])
                # Always persist collected scan logs
                if collected_logs:
                    s.logs_json = json.dumps(collected_logs)
                s.completed_at = datetime.now(UTC)
                await session.commit()

            # Broadcast scan_complete AFTER DB commit so /plan endpoint sees COMPLETED status
            if "error" in result:
                await ws_manager.broadcast(scan_id, {
                    "type": "scan_error",
                    "error": result["error"],
                })
            else:
                await ws_manager.broadcast(scan_id, {
                    "type": "scan_complete",
                    "summary": result["summary"],
                })

        except Exception as exc:
            logger.exception("Scan %d failed", scan_id)
            from app.database import async_session

            async with async_session() as session:
                s = (await session.execute(
                    select(Scan).where(Scan.id == scan_id)
                )).scalar_one()
                s.status = ScanStatus.FAILED
                s.error_message = str(exc)[:500]
                s.completed_at = datetime.now(UTC)
                await session.commit()

            await ws_manager.broadcast(scan_id, {
                "type": "scan_error",
                "error": str(exc)[:500],
            })

    asyncio.create_task(_run_crawl())

    return _scan_to_response(scan)


# ---------------------------------------------------------------------------
# GET /api/scan/{scan_id} — get scan result
# ---------------------------------------------------------------------------


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get scan result by ID."""
    query = select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    scan = (await db.execute(query)).scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _scan_to_response(scan)


# ---------------------------------------------------------------------------
# POST /api/scan/{scan_id}/plan — AI test plan generation
# ---------------------------------------------------------------------------

_PLAN_SYSTEM = """\
You are a senior QA engineer creating a test plan based on actual crawl data and \
**real interaction observations**.

CRITICAL RULES:
1. ONLY reference elements, selectors, URLs, and text that actually exist in the crawl data.
2. NEVER invent elements that don't exist (no "menu1", no fake selectors).
3. Use EXACT text strings from the crawl data (copy-paste, do not paraphrase).
4. Group tests by category with clear priority.
5. For all text assertions, set case_insensitive: true to handle dynamic casing.
6. Respond in the language specified by the user.
7. FORM FIELD RULE: For tests involving forms, reference the EXACT field data from crawl data:
   - Use placeholder text as-is (e.g., if placeholder is use NOT "Email")
   - Use label text as-is (e.g., if label is keep NOT "Password")
   - For auth_fields, set the "label" to match the actual form field label/placeholder from crawl data
   - NEVER translate form field labels or placeholders into another language
8. For auth_fields in test entries: copy the exact label/placeholder from the crawl data forms.
   Example: if crawl shows {{placeholder: label: "email address"}}, then auth_fields should be:
   {{"key": "email", "label": "email address", "type": "email", "required": true}}
9. **OBSERVATION-BASED PLANNING**: The "Interaction Observations" section below contains
   REAL results from actually clicking each element. DO NOT GUESS what happens —
   use the observed change type (page_navigation, modal_opened, anchor_scroll, section_change)
   to decide how to assert test results:
   - page_navigation → assert URL change
   - page_navigation + NAVIGATED PAGE FIELDS → this is a FORM PAGE (login/signup).
     Use the exact placeholder/label from navigated_page_fields for auth_fields.
   - modal_opened → assert new modal text is visible (use new_text from observation)
   - anchor_scroll → assert section text is visible (NOT URL change)
   - section_change → assert new content is visible (use new_text from observation)
10. **LOGIN/FORM PAGE RULE**: When an observation has change_type "page_navigation" AND
   navigated_page_fields, the click leads to a SEPARATE FORM PAGE (not a modal).
   - auth_fields MUST use the EXACT placeholder/label from navigated_page_fields
   - Example: if navigated_page_fields shows placeholder=use NOT "Email"
   - NEVER translate, NEVER guess — copy-paste the exact text from the data
11. **NO SECTION NAVIGATION TESTS**: Do NOT generate tests that only navigate to a page section
   (e.g., "section navigation", "navigate to About page", "service section check").
   Section navigation is ALREADY covered by the nav_menu_test in the "basic" category.
   Instead, for sections with interactive elements, generate INTERACTION tests:
   - accordion → test expand/collapse with actual FAQ items
   - modal → test open/close with actual trigger buttons
   - tab → test tab switching with actual tab labels
   - carousel → test slide navigation
   - form → test input validation with actual fields
12. **NEGATIVE CHECK — ERROR DETECTION**: For form tests, consider both success and
   error states. After submit, if the page stays on the same URL AND shows error text
   (e.g., "error", "invalid", "failure"), the test should detect this as failure.
   Happy-path tests should assert URL change or success text; error-path tests should
   assert error message visibility.
13. **LOGIN MUST VERIFY REDIRECT**: Login tests MUST verify the user LEFT the login page.
   If observation shows after.url → assert url_contains with that exact path.
   If redirect target is unknown → assert url_not_contains with login page path.
   NEVER guess redirect paths like "/dashboard" unless observed.
   Test descriptions should say "Verify redirect away from login", NOT "Verify login page content".
14. **NO LANGUAGE-CHECKING TESTS**: NEVER generate tests that verify the page language
   (e.g., "Verify English content", "Check Korean text"). Language is NOT a test target.
   All assert text must be EXACT text from crawl data, not invented content.

## Output Format

Create a JSON test plan with these categories. Only include categories that have matching data:

CATEGORY "basic" - Basic Health Check (auto_selected: true):
- broken_link_check: Check all broken links found
- nav_menu_test: Click each navigation menu item and verify page loads
- page_load_test: Verify all scanned pages load without errors

CATEGORY "forms" - Form Validation (auto_selected: true, only if forms found):
- For each form found, generate an input validation test
- Use actual field names and selectors

CATEGORY "auth" - Authentication (only if login_form or signup detected):
- Login and signup are SEPARATE tests — NEVER combine them in one test.
- If AUTH page_type is "login" in observations → generate login test ONLY for that page.
- If AUTH page_type is "registration" in observations → generate signup test ONLY for that page.
- A signup page MUST NOT be used for a login test (different forms, different fields).
- Mark auth_fields and requires_auth as needed.

CATEGORY "business" - Business Flows (based on detected features):
- Only for features actually detected in the crawl
- Use the business test hints above as guidance
- Test names and descriptions MUST reflect actual observed behavior, NOT generic labels
- WRONG: "Product Browsing Test" (generic — no "product" in observations)
- WRONG: "section navigation test" (this is just section navigation — ALREADY covered by nav menu test)
- RIGHT: "FAQ accordion expand/collapse test" (tests INTERACTIVE BEHAVIOR within a section)
- RIGHT: "login modal open/input test" (tests INTERACTIVE BEHAVIOR triggered by click)

IMPORTANT — SELECTOR-FIRST RULE:
- For each test, include the exact CSS selectors from the observation data in "actual_elements".
- The selectors from observations are PROVEN to work (they were actually clicked during crawling).
- Tests will use these selectors to find elements, NOT text matching.
- Include the access path: how to reach each element (e.g., "homepage → click a[href='#login'] → modal").

For each test provide:
{{
    "id": "t1",
    "name": "Test name",
    "description": "What this test does",
    "priority": "high" | "medium" | "low",
    "estimated_time": 30,
    "requires_auth": false,
    "selected": true/false,
    "auth_fields": [],
    "test_data_fields": [],
    "actual_elements": ["selector or text used"],
    "access_path": "homepage → click selector → result"
}}

Return ONLY valid JSON in this exact structure:
{{
    "categories": [
        {{
            "id": "basic",
            "name": "Category Name",
            "auto_selected": true,
            "tests": [...]
        }}
    ]
}}\
"""

_PLAN_USER = """\
Language: {language}

## Site Info
- URL: {target_url}
- Pages scanned: {total_pages}
- Detected features: {detected_features}
- Site type: {site_type} (confidence: {site_type_confidence})
- Broken links found: {broken_count}

## Crawl Data
{crawl_data}

### Broken Links
{broken_links_json}

### Interaction Observations (REAL click results — DO NOT GUESS)
{observations_json}

## Business Test Hints (based on site type)
{business_hints}

## Reference Documents
{reference_documents}

## Special Instructions
{special_instructions}\
"""


@router.post("/{scan_id}/plan", response_model=ScanPlanResponse)
async def generate_plan(
    scan_id: int,
    body: ScanPlanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate an AI test plan from scan results."""
    query = select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    scan = (await db.execute(query)).scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status not in (ScanStatus.COMPLETED, ScanStatus.PLANNED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot generate plan in '{scan.status.value}' status",
        )

    pages = _parse_json(scan.pages_json) or []
    broken = _parse_json(scan.broken_links_json) or []
    features = _parse_json(scan.detected_features) or []
    summary = _parse_json(scan.summary_json) or {}
    observations = _parse_json(getattr(scan, "observations_json", None)) or []

    # Collect elements for the prompt
    nav_menus = []
    forms = []
    buttons = []
    links_sample = []
    for p in pages:
        nav_menus.extend(p.get("nav_menus", []))
        forms.extend(p.get("forms", []))
        buttons.extend(p.get("buttons", []))
        for link in p.get("links", [])[:10]:
            links_sample.append({"text": link.get("text", ""), "href": link.get("href", "")})
        # Also collect per-page observations
        if not observations:
            observations.extend(p.get("observations", []))

    # Truncate for prompt size
    def _trunc_json(obj: Any, limit: int = 3000) -> str:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
        return s[:limit] if len(s) > limit else s

    # Build site type info for prompt
    site_type_info = summary.get("site_type") or {}
    site_type_name = (
        site_type_info.get("type", "unknown") if isinstance(site_type_info, dict) else "unknown"
    )
    site_type_conf = (
        site_type_info.get("confidence", 0.0) if isinstance(site_type_info, dict) else 0.0
    )

    # Build business hints from templates (site-type + cross-cutting)
    business_hints_lines = []
    hint_covered: set[str] = set()
    for st in [site_type_name] + [k for k in BUSINESS_TEMPLATES if k != site_type_name]:
        for tmpl in BUSINESS_TEMPLATES.get(st, []):
            req_feat = tmpl.get("requires_feature", "")
            if req_feat and req_feat not in features:
                continue
            if req_feat in hint_covered:
                continue
            if req_feat:
                hint_covered.add(req_feat)
            name = tmpl.get("name_en", "")
            desc = tmpl.get("desc_en", "")
            business_hints_lines.append(f"- {name}: {desc}")
    business_hints = (
        "\n".join(business_hints_lines)
        if business_hints_lines
        else "No specific business tests for this site type."
    )

    # Build special instructions based on detected features
    special_parts: list[str] = []
    if "spa" in features:
        special_parts.append(
            "SPA SITE DETECTED:\n"
            "- Do NOT assert URL changes after menu/link clicks.\n"
            "- Instead, assert that the target section text is visible (text_visible).\n"
            "- For anchor links (#section), only verify the section content is visible.\n"
            "- Consider modal-based login (overlay popup, not page navigation).\n"
            "- Anchor links scroll within the same page — do NOT treat them as page navigations."
        )
    if "sticky_header" in features:
        special_parts.append(
            "STICKY/FIXED HEADER DETECTED:\n"
            "- Menu items may be hidden behind the sticky header after scrolling.\n"
            "- Add a scroll_to_top (scroll 0,0,0) step before clicking header navigation items."
        )
    special_parts.append(
        "TEST INDEPENDENCE:\n"
        "- Each test MUST start with a navigate step to the base URL.\n"
        "- Tests are independent — a previous test failure must NOT affect the next test.\n"
        "- For login tests, always start from the home page."
    )

    # Add pattern summary to tell AI what's already covered
    matched_patterns = match_elements_to_patterns(pages, observations)
    pattern_hint = build_pattern_summary(matched_patterns)
    if pattern_hint:
        special_parts.append(pattern_hint)

    # Auth pattern context — inject limitations and pattern hints
    # Prefer multi_step > registration > any auth pattern
    from app.auth_patterns import build_auth_context_for_ai

    best_auth: dict[str, Any] | None = None
    for obs in observations:
        auth_info = obs.get("auth_pattern")
        if not auth_info:
            continue
        pat = auth_info.get("pattern", "")
        if pat == "multi_step":
            best_auth = auth_info
            break
        if (
            auth_info.get("page_type") == "registration"
            and (best_auth is None or best_auth.get("page_type") != "registration")
        ) or best_auth is None:
            best_auth = auth_info

    if best_auth:
        auth_ctx = build_auth_context_for_ai(best_auth)
        if auth_ctx:
            special_parts.append(auth_ctx)

    special_instructions = "\n\n".join(special_parts)

    # Fetch user reference documents
    from app.routers.documents import get_user_doc_text

    ref_docs = await get_user_doc_text(user.id, db)

    # Build AI prompt (system/user split for prompt caching)
    lang = "Korean" if body.language == "ko" else "English"
    plan_crawl = {
        "nav_menus": nav_menus,
        "forms": forms,
        "buttons": buttons,
        "links": links_sample,
    }
    plan_user = _PLAN_USER.format(
        language=lang,
        target_url=scan.target_url,
        total_pages=summary.get("total_pages", len(pages)),
        detected_features=", ".join(features) if features else "none",
        site_type=site_type_name,
        site_type_confidence=f"{site_type_conf:.0%}",
        crawl_data=compress_crawl_data(plan_crawl, max_chars=9000),
        broken_links_json=_trunc_json(broken),
        broken_count=len(broken),
        observations_json=(
            compress_observations_for_ai(observations, max_tokens=6000)
            if observations
            else "No observations collected."
        ),
        business_hints=business_hints,
        reference_documents=(ref_docs[:6000] if ref_docs else "No reference documents provided."),
        special_instructions=special_instructions,
    )

    # Generate plan: default (code-only) or AI-assisted
    plan = None
    lang = body.language or "en"

    if body.use_ai_plan:
        # AI plan mode (advanced option — off by default)
        try:
            from aat.adapters import ADAPTER_REGISTRY
            from aat.core import AIConfig
            from app.routers.ai_config import get_user_ai_config

            user_cfg = await get_user_ai_config(user.id, db)
            if user_cfg:
                ai_config = AIConfig(
                    provider=user_cfg["provider"],
                    api_key=user_cfg["api_key"],
                    model=user_cfg["model"] or _DEFAULT_MODELS.get(user_cfg["provider"], ""),
                )
            else:
                ai_config = AIConfig(
                    provider=settings.ai_provider,
                    api_key=settings.ai_api_key,
                    model=settings.ai_model or _DEFAULT_MODELS.get(settings.ai_provider, ""),
                )
            adapter_cls = ADAPTER_REGISTRY.get(ai_config.provider)
            if adapter_cls is None:
                raise ValueError(f"Unknown AI provider: {ai_config.provider}")

            adapter = adapter_cls(ai_config)
            raw_response = await _ai_raw_call(adapter, plan_user, system_prompt=_PLAN_SYSTEM)
            plan = _extract_json(raw_response)

            categories = plan.get("categories", [])
            if not categories:
                logger.warning("AI returned no categories, using default plan")
                plan = None
        except Exception as exc:
            logger.warning("AI plan generation failed (%s), using default plan", exc)
            plan = None

    # Default path: generate plan from crawl data without AI
    if plan is None:
        plan = _generate_default_plan(
            scan, pages, broken, features, summary, lang, observations,
        )

    # --- Debug logging ---
    logger.debug("=== detected_features === %s", features)
    logger.debug("=== observations count === %d", len(observations))
    login_obs = [o for o in observations if "login" in str(o).lower()]
    if login_obs:
        logger.debug("=== login-related observations === %d items", len(login_obs))
        for lo in login_obs:
            logger.info("  %s", lo.get("access_path", ""))

    # --- Post-plan validation: force-add tests for detected features ---
    plan = _validate_plan_against_features(plan, features, lang)

    # --- Dedup: remove section nav tests that duplicate nav menu test ---
    plan = _dedup_section_nav_tests(plan)

    categories = plan.get("categories", [])

    # Save plan to DB
    scan.plan_json = json.dumps(plan, ensure_ascii=False)
    scan.status = ScanStatus.PLANNED
    await db.commit()

    return {"scan_id": scan_id, "categories": categories}


async def _ai_raw_call(
    adapter: Any,
    prompt: str,
    *,
    system_prompt: str | None = None,
) -> str:
    """Call AI adapter for raw text response.

    Args:
        adapter: AI adapter instance.
        prompt: User message content.
        system_prompt: Optional system message (separated for prompt caching).
    """
    client = getattr(adapter, "_client", None)
    config = getattr(adapter, "_config", None)
    model = config.model if config else ""

    # Anthropic-style (ClaudeAdapter._client = AsyncAnthropic)
    if client and hasattr(client, "messages") and hasattr(client.messages, "create"):
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        response = await client.messages.create(**kwargs)
        return response.content[0].text if response.content else ""

    # OpenAI-style (OpenAIAdapter._client = AsyncOpenAI)
    if client and hasattr(client, "chat"):
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    raise NotImplementedError("Adapter does not support raw text generation")


def _generate_default_plan(
    scan: Any,
    pages: list,
    broken: list,
    features: list,
    summary: dict,
    language: str,
    observations: list | None = None,
) -> dict:
    """Generate a default test plan from crawl data without AI."""
    ko = language == "ko"
    categories = []

    # -- Feature false-positive filter (site_type ↔ feature cross-validation) --
    site_type_info = summary.get("site_type") or {}
    site_type_name = (
        site_type_info.get("type", "unknown") if isinstance(site_type_info, dict) else "unknown"
    )
    # Infer site_type from features when crawl detection returns "unknown"
    if site_type_name == "unknown":
        _feat = set(features)
        if _feat & {"cart", "filter_sort"} or (
            "product_list" in _feat and not _feat & {"admin_panel", "board_write"}
        ):
            site_type_name = "ecommerce"
        elif _feat & {"login_form", "signup", "admin_panel"} and not _feat & {"cart", "blog"}:
            site_type_name = "saas"
        elif "blog" in _feat:
            site_type_name = "blog"
        elif "board_write" in _feat and "login_form" not in _feat:
            site_type_name = "community"

    # Features that are contextually invalid for certain site types
    _FEATURE_BLOCKLIST: dict[str, set[str]] = {
        "finance": {"board_write", "blog", "review_form", "product_list"},
        "saas": {"board_write", "blog", "product_list", "review_form"},
        "corporate": {"board_write", "product_list", "review_form", "cart"},
        "portfolio": {"board_write", "product_list", "review_form", "cart", "filter_sort"},
    }
    blocked = _FEATURE_BLOCKLIST.get(site_type_name, set())
    features = [f for f in features if f not in blocked]
    feature_set = set(features)

    # 1. Basic health check (always)
    basic_tests = []
    tid = 1

    # Broken links (always include — link health check even without known broken links)
    if broken:
        basic_tests.append({
            "id": f"t{tid}",
            "name": "Broken Link Check",
            "description": f"Found {len(broken)} broken links",
            "priority": "high",
            "estimated_time": 10 * len(broken),
            "requires_auth": False,
            "selected": True,
            "actual_elements": [b.get("url", "") for b in broken[:5]],
        })
        tid += 1
    else:
        # Even without known broken links, include a link health check
        all_links = []
        for p in pages:
            for link in p.get("links", [])[:20]:
                href = link.get("href", "")
                if href and href.startswith("http"):
                    all_links.append(href)
        if all_links:
            basic_tests.append({
                "id": f"t{tid}",
                "name": "Link Health Check",
                "description": f"Checking {len(all_links)} links on page respond normally",
                "priority": "medium",
                "estimated_time": max(5, 2 * len(all_links)),
                "requires_auth": False,
                "selected": True,
                "actual_elements": all_links[:5],
            })
            tid += 1

    # Nav menu tests
    nav_items = []
    for p in pages:
        for nav in p.get("nav_menus", []):
            for item in nav.get("items", []):
                text = (item.get("text") or "").strip()
                href = item.get("href", "")
                if text and href and len(text) < 50:
                    nav_items.append({"text": text, "href": href})
    # Deduplicate by href
    seen_hrefs: set[str] = set()
    unique_nav: list[dict] = []
    for item in nav_items:
        if item["href"] not in seen_hrefs:
            seen_hrefs.add(item["href"])
            unique_nav.append(item)

    if unique_nav:
        basic_tests.append({
            "id": f"t{tid}",
            "name": "Navigation Menu Test" if ko else "Navigation Menu Test",
            "description": (
                f"{len(unique_nav)} menu items load correctly"
                if ko
                else f"Click each of {len(unique_nav)} menu items and verify page loads"
            ),
            "priority": "high",
            "estimated_time": 10 * len(unique_nav),
            "requires_auth": False,
            "selected": True,
            "actual_elements": [f"{n['text']} ({n['href']})" for n in unique_nav[:10]],
        })
        tid += 1
    else:
        # Fallback: extract navigable links from page as pseudo-nav
        fallback_links = []
        for p in pages:
            for link in p.get("links", []):
                text = (link.get("text") or "").strip()
                href = link.get("href", "")
                if text and href and len(text) < 50 and href.startswith(("http", "/")):
                    if href not in seen_hrefs:
                        seen_hrefs.add(href)
                        fallback_links.append({"text": text, "href": href})
                if len(fallback_links) >= 10:
                    break
        if fallback_links:
            basic_tests.append({
                "id": f"t{tid}",
                "name": "Key Link Navigation" if ko else "Key Link Navigation",
                "description": (
                    f"{len(fallback_links)} discovered key links navigate correctly"
                    if ko
                    else f"Navigate {len(fallback_links)} discovered links and verify page loads"
                ),
                "priority": "medium",
                "estimated_time": 10 * len(fallback_links),
                "requires_auth": False,
                "selected": True,
                "actual_elements": [f"{n['text']} ({n['href']})" for n in fallback_links[:10]],
            })
            tid += 1

    # Page load test
    basic_tests.append({
        "id": f"t{tid}",
        "name": "Page Load Test" if ko else "Page Load Test",
        "description": (
            f"{len(pages)} scanned pages load normally"
            if ko
            else f"Verify all {len(pages)} scanned pages load without errors"
        ),
        "priority": "medium",
        "estimated_time": 5 * len(pages),
        "requires_auth": False,
        "selected": True,
        "actual_elements": [p.get("url", "") for p in pages[:5]],
    })
    tid += 1

    categories.append({
        "id": "basic",
        "name": "Basic Health Check" if ko else "Basic Health Check",
        "auto_selected": True,
        "tests": basic_tests,
    })

    # 2. Forms (if any)
    all_forms = []
    for p in pages:
        for form in p.get("forms", []):
            fields = form.get("fields", [])
            if fields:
                all_forms.append(form)

    if all_forms:
        form_tests = []
        for i, form in enumerate(all_forms[:5]):
            field_names = [
                f.get("name") or f.get("placeholder") or "field"
                for f in form.get("fields", [])
            ]
            form_tests.append({
                "id": f"t{tid}",
                "name": f"Form Input Test #{i + 1}" if ko else f"Form Input Test #{i + 1}",
                "description": (
                    f"Fields: {', '.join(field_names[:5])}" if ko
                    else f"Fields: {', '.join(field_names[:5])}"
                ),
                "priority": "medium",
                "estimated_time": 20,
                "requires_auth": False,
                "selected": True,
                "actual_elements": [form.get("selector") or form.get("action", "")],
            })
            tid += 1

        categories.append({
            "id": "forms",
            "name": "Form Validation" if ko else "Form Validation",
            "auto_selected": True,
            "tests": form_tests,
        })

    # 3. Business tests from templates (based on site type + cross-cutting features)
    def _add_template(tmpl: dict, covered: set[str]) -> dict[str, Any] | None:
        """Convert a template to a test entry if its required feature is detected."""
        req_feat = tmpl.get("requires_feature", "")
        if req_feat and req_feat not in feature_set:
            return None
        if req_feat in covered:
            return None  # already covered
        if req_feat:
            covered.add(req_feat)
        return tmpl

    covered_features: set[str] = set()
    business_tests = []

    # Phase 1: site-type-specific templates
    for tmpl in BUSINESS_TEMPLATES.get(site_type_name, []):
        if _add_template(tmpl, covered_features) is None:
            continue
        test_entry: dict[str, Any] = {
            "id": f"t{tid}",
            "name": tmpl["name_ko"] if ko else tmpl["name_en"],
            "description": tmpl["desc_ko"] if ko else tmpl["desc_en"],
            "priority": tmpl.get("priority", "medium"),
            "estimated_time": tmpl.get("estimated_time", 30),
            "requires_auth": tmpl.get("requires_auth", False),
            "selected": not tmpl.get("requires_auth", False),
        }
        if tmpl.get("auth_fields"):
            test_entry["auth_fields"] = tmpl["auth_fields"]
        if tmpl.get("test_data_fields"):
            test_entry["test_data_fields"] = tmpl["test_data_fields"]
        business_tests.append(test_entry)
        tid += 1

    # Phase 2: cross-cutting — scan ALL site types for uncovered detected features
    for other_type, other_templates in BUSINESS_TEMPLATES.items():
        if other_type == site_type_name:
            continue  # already processed
        for tmpl in other_templates:
            if _add_template(tmpl, covered_features) is None:
                continue
            test_entry = {
                "id": f"t{tid}",
                "name": tmpl["name_ko"] if ko else tmpl["name_en"],
                "description": tmpl["desc_ko"] if ko else tmpl["desc_en"],
                "priority": tmpl.get("priority", "medium"),
                "estimated_time": tmpl.get("estimated_time", 30),
                "requires_auth": tmpl.get("requires_auth", False),
                "selected": not tmpl.get("requires_auth", False),
            }
            if tmpl.get("auth_fields"):
                test_entry["auth_fields"] = tmpl["auth_fields"]
            if tmpl.get("test_data_fields"):
                test_entry["test_data_fields"] = tmpl["test_data_fields"]
            business_tests.append(test_entry)
            tid += 1

    if business_tests:
        categories.append({
            "id": "business",
            "name": "Business Flows" if ko else "Business Flows",
            "auto_selected": False,
            "tests": business_tests,
        })

    # 4. Standard element test patterns
    matched = match_elements_to_patterns(pages, observations or [])
    pattern_category = build_pattern_tests(matched, language)
    if pattern_category:
        categories.append(pattern_category)

    return {"categories": categories}


def _extract_json(text: str) -> dict:
    """Extract JSON object from AI response text."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in markdown code fence
    import re
    patterns = [
        r"```json\s*([\s\S]*?)```",
        r"```\s*([\s\S]*?)```",
        r"\{[\s\S]*\}"]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1) if match.lastindex else match.group(0)
            try:
                return json.loads(candidate.strip())
            except json.JSONDecodeError:
                continue

    raise ValueError(f"No valid JSON found in response: {text[:200]}")


def _build_observation_table(observations: list[dict]) -> str:
    """Convert raw observations into compact tagged format for AI.

    Uses compress_observations_for_ai() for consistent token-efficient output.
    """
    return compress_observations_for_ai(observations, max_tokens=20000)


# ---------------------------------------------------------------------------
# POST /api/scan/{scan_id}/execute — run selected tests
# ---------------------------------------------------------------------------

_EXECUTE_SYSTEM = """\
You are an expert QA engineer generating AWT test scenario JSON.
Generate EXACTLY ONE scenario per selected test. Do NOT merge multiple tests into one scenario. \
Do NOT skip any selected test.

## ========== ABSOLUTE RULES (NEVER VIOLATE) ==========

1. **SELECTOR-FIRST**: Every click/type target MUST include "selector" from the observation data.
   WRONG: {{"text": "features"}}
   RIGHT: {{"selector": "a[href=\\"#features\\"]", "text": "features"}}

2. **ASSERT FROM OBSERVED DATA ONLY**: Assert values MUST come from the "OBSERVED new_text"
   field in the observation table below, or from crawl data text that actually exists.
   WRONG: assert value "product list" (AI guess — this text does NOT exist in observation data)
   WRONG: assert value "Product Browsing" (from test name — test names are NOT data)
   RIGHT: assert value "core features" (copy-pasted from observation new_text)

3. **MODAL FORM FIELDS**: When observation shows modal_opened with modal_form_fields,
   use the EXACT selector/placeholder from modal_form_fields for find_and_type targets.
   observation: modal_form_fields: [{{"selector": "#email", "placeholder": "enter your email"}}]
   → target: {{"selector": "#email", "text": "enter your email"}}

4. **NEVER INVENT**: Do not use any text, selector, URL, or page name that is NOT
   in the Observation Reference Table or Crawl Data below. The selected test names
   are LABELS ONLY — do NOT derive step targets or assert values from them.

5. **WAIT AFTER MODAL**: After clicking an element that opens a modal (change_type: modal_opened),
   add a wait step (1000ms) before interacting with modal fields.

6. **CASE INSENSITIVE ASSERT**: All assert steps MUST set "case_insensitive": true.

6.5. **ASSERT FORMAT — MANDATORY FIELDS**:
   Every assert step MUST include ALL of these fields:
   - "action": "assert"
   - "assert_type": "text_visible" | "url_contains" | "url_not_contains"
   - "value": the EXACT text or URL path to check (NOT the description)
   - "description": human-readable explanation
   WRONG: {{"action": "assert", "description": "Verify homepage loads"}}  ← missing assert_type & value
   RIGHT: {{"action": "assert", "assert_type": "text_visible", "value": "Products", "description": "Verify products page"}}
   An assert without assert_type + value will be REMOVED automatically.

7. **TEST INDEPENDENCE**: Each scenario MUST start with navigate to target URL.

8. **NO PHANTOM PAGES**: Do NOT assert URL changes to pages not seen in observations.
   If observation shows anchor_scroll or modal_opened, the URL does NOT change.
   Only assert URL change when observation change_type is "page_navigation".

9. **PAGE NAVIGATION + FORM FIELDS**: When observation has change_type "page_navigation"
   AND "NAVIGATED PAGE FIELDS" data, this click leads to a SEPARATE FORM PAGE (e.g., login).
   Steps to generate:
   a. navigate to target URL (homepage)
   b. find_and_click the element (e.g., link) to go to the form page
   c. For find_and_type: use EXACT placeholder/label from NAVIGATED PAGE FIELDS
      - If placeholder is target text MUST be — NOT "Email"
      - If placeholder is target text MUST be — NOT "Password"
   d. For submit button: use EXACT label from NAVIGATED PAGE FIELDS
   e. NEVER translate or guess field names — copy the EXACT text from observation data

10. **FORM SUBMIT BUTTON — CRITICAL**:
   After filling form fields (find_and_type steps), the NEXT click MUST be the
   form's own submit button — look for SUBMIT[form] in the PAGE/MODAL FIELDS.
   - SUBMIT[form] = button INSIDE the form → USE THIS for form submission
   - SUBMIT[nav] = navigation menu link → NEVER use this after form input
   - SUBMIT[body] = button outside form/nav → only use if no [form] button exists
   Example: PAGE FIELDS shows SUBMIT[form](button.btn, "next") and SUBMIT[nav](a.nav, "signup")
   → After filling email/password, click "next" (SUBMIT[form]), NOT "signup" (SUBMIT[nav])
   - The nav link "signup" is for PAGE NAVIGATION (step b above), NOT for form submission

11. **OUTCOME VERIFICATION — MANDATORY**:
   Every scenario with form interaction MUST end with an assert step AFTER submit.
   A test that clicks submit without verifying the result proves NOTHING.
   After SUBMIT[form] click → add wait (1500ms) → assert ONE of:
   a. url_contains: verify URL changed after submission
   b. text_visible: verify new content appeared (success message, next step)
   For confirm password fields, use the SAME value as the password: "TestPass123!"
   **LOGIN REDIRECT RULE (CRITICAL)**:
   Login success = URL changes away from the login page.
   - If observation after.url shows the redirect target → use url_contains with that EXACT path.
   - If redirect target is UNKNOWN → NEVER guess paths like "/dashboard" or "/home".
     Instead use url_not_contains with the login page path:
     Example: login page is at "/" → assert text_visible with post-login-only text
     Example: login page is at "/login" → assert url_not_contains "/login"
   WRONG: assert url_contains "/dashboard" (guessed — not in observation data)
   RIGHT: assert url_not_contains "/login" (verifies user LEFT the login page)
   RIGHT: assert url_contains "/inventory" (EXACT path from observation after.url)
   Use url_contains or text_visible from the observation "new_text" / "after.url"
   which shows the post-redirect page content. For example, if after.url is "/board"
   and new_text includes "board", assert text_visible "board" — NOT .

   **LOGIN ASSERT — UNIQUE TEXT RULE**:
   When asserting login success with text_visible:
   - NEVER use site-wide text that appears on BOTH the login page AND the post-login page.
     Site names, logos, navigation items exist on ALL pages → useless for login verification.
   - ONLY use text that appears EXCLUSIVELY after login:
     Good: "Products", "Dashboard", "Logout", "My Account", cart icon text
     Bad: "Swag Labs" (site name — visible on login page too)
   - Best practice: combine url assertion + text assertion for maximum reliability.

   **NO PLACEHOLDER ASSERTS**:
   NEVER use input field placeholder text (e.g., "Username", "Password", "Email",
   "First Name", "Zip/Postal Code") as a text_visible assert value.
   Placeholders are inside input elements, NOT visible page text.
   WRONG: assert text_visible "Username" (this is an input placeholder)
   RIGHT: assert text_visible "Products" (this is actual page heading text)
   RIGHT: assert url_contains "/inventory" (URL-based verification)

   **REGISTRATION REDIRECT RULE**: After REGISTRATION form submit → the page redirects
   to login page or main page. Assert the REDIRECTED page (e.g., url_contains "/login"
   or text_visible for login page text). NEVER assert registration form text like
   "step 1" or "account info" — those are from BEFORE submission.

12. **NO LANGUAGE-CHECKING ASSERTS**:
   NEVER generate scenarios that verify the LANGUAGE of the page
   (e.g., "Verify page content is in English", "Check Korean text").
   Language verification is NOT a valid E2E test.
   Assert values MUST be EXACT text copied from the Observation Table or Crawl Data.
   WRONG: assert text_visible "page content is in English"
   WRONG: assert text_visible "Fix it like this" (invented English text)
   RIGHT: assert text_visible (actual text from observation data)
   RIGHT: assert text_visible "Welcome back" (actual text from crawl data)

## ========== END ABSOLUTE RULES ==========

## Output Format
Return ONLY a valid JSON array. Each object:
{{
  "id": "SC-001",
  "name": "Test name",
  "description": "Test description",
  "steps": [
    {{"step": 1, "action": "navigate", "value": "TARGET_URL", "description": "Navigate to homepage"}},
    {{"step": 2, "action": "find_and_click", "target": {{"selector": "a[href=\\"#login\\"]", "text": }}, "description": "Click login button"}},
    {{"step": 3, "action": "wait", "value": "1000", "description": "Wait for modal animation"}},
    {{"step": 4, "action": "find_and_type", "target": {{"selector": "#email", "text": }}, "value": "awttest@example.com", "description": "Enter email"}},
    {{"step": 5, "action": "find_and_click", "target": {{"selector": "button[type=submit]", "text": }}, "description": "Click submit button (SUBMIT[form])"}},
    {{"step": 6, "action": "wait", "value": "1500", "description": "Wait for page transition after form submit"}},
    {{"step": 7, "action": "assert", "assert_type": "text_visible", "value": "Welcome", "description": "Verify login success", "case_insensitive": true}}
  ]
}}

Actions: navigate, find_and_click, find_and_type, assert, wait, scroll
Target format: {{"selector": "CSS_FROM_OBSERVATION", "text": "VISIBLE_TEXT_FROM_OBSERVATION"}}

FINAL CHECK before responding:
1. For every assert value, verify it appears verbatim in the Observation Reference Table or Crawl Data.
   If not, REMOVE that assert step.
2. Does every form scenario end with assert AFTER submit? If last step is find_and_click (submit),
   ADD wait + assert.
3. Does every login scenario assert URL change (url_contains with observed path, or url_not_contains login path)?
   A login test that only checks text on the login page is WRONG.
4. Is every assert value REAL text from page data? No invented text, no language checks.
5. Does every assert step have assert_type + value (not just description)?

Return ONLY valid JSON array.\
"""

_EXECUTE_USER = """\
{extra_instructions}

## Reference Documents
{reference_documents}
{language_instruction}
## Target URL: {target_url}
## Batch: {batch_count} test(s) to generate

## Observation Reference Table
Each row = one observed interaction. Use these EXACT selectors and texts.
{observation_table}

## Crawl Data (forms with field selectors)
{crawl_data}

## Selected Tests (LABELS ONLY — do NOT use these names as test data)
{selected_tests}

## User-Provided Data
{user_data}

For empty user data fields, use reasonable dummy data:
- email: use "awttest@example.com"
- password: use "TestPass123!"
- text fields: use contextually appropriate text\
"""


def _chunk_tests(tests: list[dict], batch_size: int = 3) -> list[list[dict]]:
    """Split selected tests into batches for safer AI generation."""
    return [tests[i : i + batch_size] for i in range(0, len(tests), batch_size)]


@router.post("/{scan_id}/execute")
async def execute_scan_tests(
    scan_id: int,
    body: ScanExecuteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate scenarios from selected tests and create a test execution.

    Returns immediately with test_id + status="generating".
    AI scenario generation runs in the background with parallel batch calls.
    """
    query = select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    scan = (await db.execute(query)).scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status != ScanStatus.PLANNED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot execute in '{scan.status.value}' status. Generate a plan first.",
        )

    plan = _parse_json(scan.plan_json)
    if not plan:
        raise HTTPException(status_code=422, detail="No test plan found")

    # Extract selected test details from plan
    selected_details = []
    for cat in plan.get("categories", []):
        for test in cat.get("tests", []):
            if test.get("id") in body.selected_tests:
                selected_details.append(test)

    if not selected_details:
        raise HTTPException(status_code=422, detail="No valid tests selected")

    # Gather crawl data for context
    pages = _parse_json(scan.pages_json) or []
    observations = _parse_json(getattr(scan, "observations_json", None)) or []
    crawl_context: dict[str, list] = {"nav_menus": [], "forms": [], "buttons": []}
    for p in pages[:5]:
        crawl_context["nav_menus"].extend(p.get("nav_menus", []))
        crawl_context["forms"].extend(p.get("forms", []))
        crawl_context["buttons"].extend(p.get("buttons", []))
        # Collect per-page observations as fallback
        if not observations:
            observations.extend(p.get("observations", []))

    user_data = {**body.auth_data, **body.test_data}

    # Validate AI adapter is available (fail fast before creating test)
    try:
        from aat.adapters import ADAPTER_REGISTRY
        from aat.core import AIConfig
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"AAT core not installed: {exc}") from exc

    from app.routers.ai_config import get_user_ai_config

    user_cfg = await get_user_ai_config(user.id, db)
    if user_cfg:
        ai_config = AIConfig(
            provider=user_cfg["provider"],
            api_key=user_cfg["api_key"],
            model=user_cfg["model"] or _DEFAULT_MODELS.get(user_cfg["provider"], ""),
            max_tokens=16000,
        )
    else:
        # Ollama is a local provider that doesn't require an API key
        provider = settings.ai_provider
        api_key = settings.ai_api_key
        if provider == "ollama":
            # Ollama uses localhost by default, API key is optional (can be used as URL override)
            api_key = api_key or "http://localhost:11434"
        elif not api_key:
            raise HTTPException(status_code=400, detail="no_ai_key_configured")
        ai_config = AIConfig(
            provider=provider,
            api_key=api_key,
            model=settings.ai_model or _DEFAULT_MODELS.get(provider, ""),
            max_tokens=16000,
        )
    adapter_cls = ADAPTER_REGISTRY.get(ai_config.provider)
    if adapter_cls is None:
        raise HTTPException(status_code=503, detail=f"Unknown AI provider: {ai_config.provider}")

    # Build extra instructions based on detected features
    features = _parse_json(scan.detected_features) or []
    extra_parts: list[str] = []
    if "spa" in features:
        extra_parts.append(
            "SPA SITE: Do NOT assert URL changes. Use text_visible assertions. "
            "Anchor links scroll within the page — assert section content is visible."
        )
    if "sticky_header" in features:
        extra_parts.append(
            "STICKY HEADER: Add scroll(0,0,0) before clicking header menu items."
        )

    # Tell AI which elements already have standard tests
    matched_patterns = match_elements_to_patterns(pages, observations)
    pattern_hint = build_pattern_summary(matched_patterns)
    if pattern_hint:
        extra_parts.append(pattern_hint)

    # Auth pattern context — prefer multi_step > registration > any
    from app.auth_patterns import build_auth_context_for_ai

    best_auth: dict[str, Any] | None = None
    for obs in observations:
        auth_info = obs.get("auth_pattern")
        if not auth_info:
            continue
        pat = auth_info.get("pattern", "")
        if pat == "multi_step":
            best_auth = auth_info
            break
        if (
            auth_info.get("page_type") == "registration"
            and (best_auth is None or best_auth.get("page_type") != "registration")
        ) or best_auth is None:
            best_auth = auth_info

    if best_auth:
        auth_ctx = build_auth_context_for_ai(best_auth)
        if auth_ctx:
            extra_parts.append(auth_ctx)

    extra_instructions = "\n".join(extra_parts) if extra_parts else ""

    # Fetch user reference documents
    from app.routers.documents import get_user_doc_text

    ref_docs = await get_user_doc_text(user.id, db)

    # --- Dynamic token budget allocation ---
    max_input_tokens = 40_000
    template_tokens = 5000
    overhead_tokens = 1000
    budget = max_input_tokens - template_tokens - overhead_tokens

    user_data_str = json.dumps(user_data, ensure_ascii=False)
    extra_str = extra_instructions
    fixed_tokens = (len(user_data_str) + len(extra_str)) // 3

    remaining = max(budget - fixed_tokens, 3000)
    ref_limit = int(remaining * 0.20) * 3
    crawl_limit = int(remaining * 0.15) * 3
    selected_limit = int(remaining * 0.15) * 3
    obs_tokens = int(remaining * 0.50)

    ref_docs_str = ref_docs or "No reference documents provided."
    if len(ref_docs_str) > ref_limit:
        ref_docs_str = ref_docs_str[:ref_limit] + "\n... (truncated)"

    observation_table = compress_observations_for_ai(observations, max_tokens=obs_tokens)

    def _trunc(obj: Any, limit: int = 4000) -> str:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
        return s[:limit] if len(s) > limit else s

    crawl_data_str = compress_crawl_data(crawl_context, max_chars=crawl_limit)
    selected_str = _trunc(selected_details, selected_limit)

    logger.info("Token budget (scan_id=%d): obs=%dt, crawl=%dt, selected=%dt, ref=%dt",
                scan_id, len(observation_table) // 3, len(crawl_data_str) // 3,
                len(selected_str) // 3, len(ref_docs_str) // 3)

    # Clean up stuck tests for this user before creating a new one
    from app.models import Test, TestStatus

    stuck_cutoff = datetime.now(UTC) - timedelta(
        minutes=settings.stuck_timeout_minutes
    )
    stuck_result = await db.execute(
        select(Test).where(
            Test.user_id == user.id,
            Test.status.in_([TestStatus.RUNNING, TestStatus.QUEUED]),
            Test.updated_at < stuck_cutoff,
        )
    )
    for stuck_test in stuck_result.scalars().all():
        stuck_test.status = TestStatus.FAILED
        stuck_test.error_message = (
            f"Auto-cancelled: stuck {stuck_test.status.value}"
            f" > {settings.stuck_timeout_minutes} min"
        )
        stuck_test.updated_at = datetime.now(UTC)
        logger.warning(
            "Pre-exec cleanup: auto-failed stuck test %d for user %s",
            stuck_test.id, user.id,
        )

    # --- Scenario cache check (skip AI if site unchanged) ---
    force_regen = getattr(body, "force_regenerate", False)
    fingerprint = compute_scan_fingerprint(pages, observations)
    fuzzy_fingerprint = compute_structure_fingerprint(pages, observations)
    tests_hash = compute_tests_hash(body.selected_tests)

    # Cache TTL: 24 hours
    cache_ttl = timedelta(hours=24)
    cache_cutoff = datetime.now(UTC) - cache_ttl

    if not force_regen:
        # 1. Exact fingerprint match (same site structure)
        cache_hit = (await db.execute(
            select(ScenarioCache).where(
                ScenarioCache.user_id == user.id,
                ScenarioCache.target_url == str(scan.target_url),
                ScenarioCache.scan_fingerprint == fingerprint,
                ScenarioCache.selected_tests_hash == tests_hash,
                ScenarioCache.created_at > cache_cutoff,
            ).order_by(ScenarioCache.created_at.desc()).limit(1)
        )).scalar_one_or_none()

        # 2. Fuzzy fallback: match by structure fingerprint (ignores minor changes)
        if cache_hit is None:
            cache_hit = (await db.execute(
                select(ScenarioCache).where(
                    ScenarioCache.user_id == user.id,
                    ScenarioCache.target_url == str(scan.target_url),
                    ScenarioCache.scan_fingerprint == fuzzy_fingerprint,
                    ScenarioCache.selected_tests_hash == tests_hash,
                    ScenarioCache.created_at > cache_cutoff,
                ).order_by(ScenarioCache.created_at.desc()).limit(1)
            )).scalar_one_or_none()
            if cache_hit:
                logger.info("Cache FUZZY HIT (scan_id=%d): structure unchanged", scan_id)

        if cache_hit:
            test = Test(
                user_id=user.id,
                target_url=scan.target_url,
                status=TestStatus.QUEUED,
                scenario_yaml=cache_hit.scenario_yaml,
                steps_total=cache_hit.steps_total,
            )
            db.add(test)
            await db.commit()
            await db.refresh(test)
            logger.info(
                "Cache HIT (scan_id=%d): reusing cached scenarios "
                "(fingerprint=%s, %d steps). AI calls saved.",
                scan_id, fingerprint, cache_hit.steps_total,
            )
            return {
                "test_id": test.id,
                "status": "queued",
                "cached": True,
                "message": "No site changes detected — reusing previous scenarios.",
            }

    # Create Test record with GENERATING status (no scenario_yaml yet)
    test = Test(
        user_id=user.id,
        target_url=scan.target_url,
        status=TestStatus.GENERATING,
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)

    test_id = test.id

    # Detect site language for prompt injection
    all_page_data = pages[0] if pages else {}
    site_lang = detect_site_language(all_page_data, observations)
    lang_instruction = build_language_instruction(site_lang)
    logger.info("Execute: detected site language = %s (scan_id=%d)", site_lang, scan_id)

    # Launch background scenario generation with parallel AI calls
    asyncio.create_task(_bg_generate_scenarios(
        test_id=test_id,
        target_url=str(scan.target_url),
        adapter_cls=adapter_cls,
        ai_config=ai_config,
        selected_details=selected_details,
        observations=observations,
        pages=pages,
        crawl_context=crawl_context,
        user_data=user_data,
        user_data_str=user_data_str,
        extra_str=extra_str,
        ref_docs_str=ref_docs_str,
        observation_table=observation_table,
        crawl_data_str=crawl_data_str,
        selected_str=selected_str,
        selected_limit=selected_limit,
        max_input_tokens=max_input_tokens,
        best_auth=best_auth,
        additional_yaml=body.additional_yaml,
        language_instruction=lang_instruction,
        fingerprint=fingerprint,
        fuzzy_fingerprint=fuzzy_fingerprint,
        tests_hash=tests_hash,
    ))

    return {"test_id": test_id, "status": "generating"}


async def _gen_one_batch(
    adapter: Any,
    prompt: str,
    batch_idx: int,
    observations: list[dict],
    crawl_context: dict,
    user_data_str: str,
    extra_str: str,
    ref_docs_str: str,
    target_url: str,
    batch: list[dict],
    language_instruction: str = "",
) -> list:
    """Generate scenarios for a single batch with retry logic."""
    def _trunc(obj: Any, limit: int = 4000) -> str:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
        return s[:limit] if len(s) > limit else s

    for attempt in range(2):
        try:
            batch_scenarios = await adapter.generate_scenarios(
                prompt, system_prompt=_EXECUTE_SYSTEM,
            )
            return batch_scenarios
        except Exception as exc:
            err_msg = str(exc).lower()
            if attempt == 0 and ("json" in err_msg or "truncat" in err_msg):
                logger.warning(
                    "Batch %d JSON/truncation error, retrying: %s",
                    batch_idx, str(exc)[:200],
                )
                continue
            if "token" in err_msg and (
                "limit" in err_msg or "rate" in err_msg or "tpm" in err_msg
            ):
                logger.warning("Batch %d token limit, retrying minimal", batch_idx)
                compressed_obs = compress_observations_for_ai(
                    observations, max_tokens=2000,
                )
                retry_prompt = _EXECUTE_USER.format(
                    target_url=target_url,
                    crawl_data=compress_crawl_data(crawl_context, max_chars=1500),
                    observation_table=compressed_obs,
                    selected_tests=_trunc(batch, 1500),
                    user_data=user_data_str,
                    extra_instructions=extra_str,
                    reference_documents="(omitted to fit token limit)",
                    batch_count=len(batch),
                    language_instruction=language_instruction,
                )
                batch_scenarios = await adapter.generate_scenarios(
                    retry_prompt, system_prompt=_EXECUTE_SYSTEM,
                )
                return batch_scenarios
            raise
    return []


async def _bg_generate_scenarios(
    *,
    test_id: int,
    target_url: str,
    adapter_cls: type,
    ai_config: Any,
    selected_details: list[dict],
    observations: list[dict],
    pages: list[dict],
    crawl_context: dict,
    user_data: dict,
    user_data_str: str,
    extra_str: str,
    ref_docs_str: str,
    observation_table: str,
    crawl_data_str: str,
    selected_str: str,
    selected_limit: int,
    max_input_tokens: int,
    best_auth: dict[str, Any] | None,
    additional_yaml: str,
    language_instruction: str = "",
    fingerprint: str = "",
    fuzzy_fingerprint: str = "",
    tests_hash: str = "",
) -> None:
    """Background task: parallel AI batch generation + post-processing."""
    from app.database import async_session

    def _trunc(obj: Any, limit: int = 4000) -> str:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
        return s[:limit] if len(s) > limit else s

    try:
        adapter = adapter_cls(ai_config)

        # --- Tier 1: Pattern-based scenario builder (no AI) ---
        from app.scenario_builder import build_scenarios_from_observations

        pattern_scenarios_raw, ai_tests = build_scenarios_from_observations(
            selected_details, observations, target_url, user_data,
            pages=pages,
        )

        # Convert pattern-built dicts to Scenario model objects
        from aat.core import Scenario as ScenarioModel

        pattern_scenarios: list = []
        for sc_dict in pattern_scenarios_raw:
            try:
                pattern_scenarios.append(ScenarioModel.model_validate(sc_dict))
            except Exception as exc:
                logger.warning("Pattern scenario validation failed: %s", exc)
                # Find the matching test detail and route to AI
                sc_name = sc_dict.get("name", "")
                matched = next(
                    (t for t in selected_details if t.get("name") == sc_name),
                    None,
                )
                if matched and matched not in ai_tests:
                    ai_tests.append(matched)

        logger.info(
            "BG: Pattern builder produced %d scenarios, %d tests → AI (test_id=%d)",
            len(pattern_scenarios), len(ai_tests), test_id,
        )

        # --- Tier 3: AI generation for remaining tests ---
        ai_scenarios: list = []
        if ai_tests:
            batches = _chunk_tests(ai_tests, batch_size=3)
            logger.info(
                "BG: Splitting %d AI tests into %d batches (test_id=%d)",
                len(ai_tests), len(batches), test_id,
            )

            batch_prompts: list[str] = []
            for batch_idx, batch in enumerate(batches):
                batch_selected_str = _trunc(batch, selected_limit)
                batch_prompt = _EXECUTE_USER.format(
                    target_url=target_url,
                    crawl_data=crawl_data_str,
                    observation_table=observation_table,
                    selected_tests=batch_selected_str,
                    user_data=user_data_str,
                    extra_instructions=extra_str,
                    reference_documents=ref_docs_str,
                    batch_count=len(batch),
                    language_instruction=language_instruction,
                )

                estimated_total = (len(batch_prompt) + len(_EXECUTE_SYSTEM)) // 3
                if estimated_total > max_input_tokens:
                    logger.warning(
                        "BG: Batch %d prompt %d tokens (limit %d), trimming",
                        batch_idx, estimated_total, max_input_tokens,
                    )
                    trimmed_obs = compress_observations_for_ai(observations, max_tokens=3000)
                    batch_prompt = _EXECUTE_USER.format(
                        target_url=target_url,
                        crawl_data=compress_crawl_data(crawl_context, max_chars=2000),
                        observation_table=trimmed_obs,
                        selected_tests=_trunc(batch, 2000),
                        user_data=user_data_str,
                        extra_instructions=extra_str,
                        reference_documents=ref_docs_str[:3000],
                        batch_count=len(batch),
                        language_instruction=language_instruction,
                    )
                batch_prompts.append(batch_prompt)

            # --- Parallel AI calls via asyncio.gather ---
            tasks = [
                _gen_one_batch(
                    adapter=adapter,
                    prompt=batch_prompts[i],
                    batch_idx=i,
                    observations=observations,
                    crawl_context=crawl_context,
                    user_data_str=user_data_str,
                    extra_str=extra_str,
                    ref_docs_str=ref_docs_str,
                    target_url=target_url,
                    batch=batch,
                    language_instruction=language_instruction,
                )
                for i, batch in enumerate(batches)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for batch_idx, result in enumerate(results):
                if isinstance(result, BaseException):
                    logger.exception(
                        "BG: Batch %d failed (test_id=%d): %s",
                        batch_idx, test_id, result,
                    )
                    raise result
                ai_scenarios.extend(result)

        # Merge pattern + AI scenarios, renumber SC-IDs sequentially
        all_scenarios: list = list(pattern_scenarios) + ai_scenarios
        for i, sc in enumerate(all_scenarios, 1):
            if hasattr(sc, "id"):
                sc.__dict__["id"] = f"SC-{i:03d}"

        scenarios = all_scenarios

        if not scenarios:
            raise ValueError("No scenarios generated (pattern + AI both empty)")

        # === Post-processing pipeline ===
        scenarios = fix_assert_steps(scenarios)
        scenarios = fix_field_targets(scenarios, observations)

        if best_auth and best_auth.get("multi_step_fields"):
            scenarios = enforce_multi_step_order(
                scenarios, best_auth["multi_step_fields"],
            )

        scenarios = fix_form_submit_steps(scenarios, observations)
        scenarios = ensure_post_submit_assert(scenarios)
        scenarios = inject_login_prefix(
            scenarios, observations, user_data,
            target_url=target_url,
        )

        # Validate assert steps (auto-remove/convert bad asserts)
        scenarios = validate_asserts(scenarios, observations, pages)

        # Build a full prompt context for validation retry
        validation_prompt = _EXECUTE_USER.format(
            target_url=target_url,
            crawl_data=crawl_data_str,
            observation_table=observation_table,
            selected_tests=selected_str,
            user_data=user_data_str,
            extra_instructions=extra_str,
            reference_documents=ref_docs_str,
            batch_count=len(selected_details),
            language_instruction=language_instruction,
        )

        scenarios, _validation = await validate_and_retry(
            scenarios, observations, pages, adapter, validation_prompt,
            system_prompt=_EXECUTE_SYSTEM,
        )

        # Serialize to YAML
        scenario_dicts = [
            s.model_dump(mode="json", exclude_none=True)
            for s in scenarios
        ]
        scenario_yaml = yaml.safe_dump(
            scenario_dicts,
            default_flow_style=False,
            allow_unicode=True,
        )

        # Merge additional_yaml if provided
        if additional_yaml and additional_yaml.strip():
            scenario_yaml = scenario_yaml + "\n" + additional_yaml.strip() + "\n"

        total_steps = sum(len(s.steps) for s in scenarios)

        # Update Test record: GENERATING → REVIEW (user reviews before execution)
        async with async_session() as session:
            from app.models import Test, TestStatus

            test = (await session.execute(
                select(Test).where(Test.id == test_id)
            )).scalar_one()
            test.scenario_yaml = scenario_yaml
            test.steps_total = total_steps
            test.status = TestStatus.REVIEW
            test.updated_at = datetime.now(UTC)

            # Save to scenario cache for future reuse (exact + fuzzy)
            if fingerprint and tests_hash:
                cache_entry = ScenarioCache(
                    user_id=test.user_id,
                    target_url=target_url,
                    scan_fingerprint=fingerprint,
                    selected_tests_hash=tests_hash,
                    scenario_yaml=scenario_yaml,
                    steps_total=total_steps,
                )
                session.add(cache_entry)
                # Also save with fuzzy fingerprint for structure-level matching
                if fuzzy_fingerprint and fuzzy_fingerprint != fingerprint:
                    fuzzy_entry = ScenarioCache(
                        user_id=test.user_id,
                        target_url=target_url,
                        scan_fingerprint=fuzzy_fingerprint,
                        selected_tests_hash=tests_hash,
                        scenario_yaml=scenario_yaml,
                        steps_total=total_steps,
                    )
                    session.add(fuzzy_entry)
                logger.info(
                    "BG: Cached scenarios (exact=%s, fuzzy=%s, tests=%s)",
                    fingerprint, fuzzy_fingerprint, tests_hash,
                )

            await session.commit()

        # Broadcast scenarios_ready so frontend transitions to review screen
        from app.ws import ws_manager as _ws

        await _ws.broadcast(test_id, {
            "type": "scenarios_ready",
            "test_id": test_id,
            "steps_total": total_steps,
            "scenario_count": len(scenarios),
        })

        logger.info(
            "BG: Scenario generation complete → REVIEW (test_id=%d): %d scenarios, %d steps",
            test_id, len(scenarios), total_steps,
        )

    except Exception as exc:
        logger.exception("BG: Scenario generation failed (test_id=%d)", test_id)
        # Mark test as FAILED
        try:
            async with async_session() as session:
                from app.models import Test, TestStatus

                test = (await session.execute(
                    select(Test).where(Test.id == test_id)
                )).scalar_one()
                test.status = TestStatus.FAILED
                test.error_message = f"Scenario generation failed: {str(exc)[:500]}"
                test.updated_at = datetime.now(UTC)
                await session.commit()
        except Exception:
            logger.exception("BG: Failed to update test status (test_id=%d)", test_id)


# ---------------------------------------------------------------------------
# WebSocket — per-scan live progress
# ---------------------------------------------------------------------------


@router.websocket("/{scan_id}/ws")
async def scan_websocket(websocket: WebSocket, scan_id: int) -> None:
    """WebSocket for live scan progress.

    Events: scan_start, page_scanned, feature_detected, scan_complete, scan_error.
    """
    await ws_manager.connect(scan_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(scan_id, websocket)
