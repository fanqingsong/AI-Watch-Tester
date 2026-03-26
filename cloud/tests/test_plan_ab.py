"""A/B Test: AI Plan vs Default Plan comparison.

Crawls real sites, generates both AI and default plans from the same
crawl data, then compares coverage and quality.

Usage:
    python -m pytest cloud/tests/test_plan_ab.py -s --timeout=600
    # or directly:
    python cloud/tests/test_plan_ab.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any
from urllib.parse import urlparse

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AWT_SECRET_KEY", "test-secret-key-for-ab-test")

# Load .env
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test sites (from cost_optimization_plan.md B1-0)
# ---------------------------------------------------------------------------

TEST_SITES: list[dict[str, str]] = [
    # Category 1: E-commerce
    {"url": "https://www.saucedemo.com", "name": "SauceDemo", "type": "ecommerce"},
    {"url": "https://magento.softwaretestingboard.com", "name": "Magento", "type": "ecommerce"},
    {"url": "https://demo.opencart.com", "name": "OpenCart", "type": "ecommerce"},
    {"url": "https://automationteststore.com", "name": "AutoTestStore", "type": "ecommerce"},
    {"url": "https://juice-shop.herokuapp.com", "name": "JuiceShop", "type": "ecommerce"},
    # Category 2: SaaS / B2B
    {"url": "https://opensource-demo.orangehrmlive.com", "name": "OrangeHRM", "type": "saas"},
    {"url": "https://thinking-tester-contact-list.herokuapp.com", "name": "ContactList", "type": "saas"},
    {"url": "https://parabank.parasoft.com", "name": "ParaBank", "type": "saas"},
    {"url": "https://practice.expandtesting.com", "name": "ExpandTest", "type": "saas"},
    # Category 3: Test sites
    {"url": "https://demoqa.com", "name": "DemoQA", "type": "test"},
    {"url": "https://the-internet.herokuapp.com", "name": "TheInternet", "type": "test"},
    {"url": "https://webdriveruniversity.com", "name": "WDUniversity", "type": "test"},
    # Category 4: Blog/Content
    {"url": "https://conduit.productionready.io", "name": "RealWorld", "type": "blog"},
    # Category 5: Multilingual (read-only, no auth)
    {"url": "https://www.coupang.com", "name": "Coupang", "type": "multilingual"},
    {"url": "https://www.uniqlo.com/jp", "name": "Uniqlo JP", "type": "multilingual"},
]


# ---------------------------------------------------------------------------
# Crawl a site
# ---------------------------------------------------------------------------

async def crawl_one(url: str, name: str) -> dict[str, Any] | None:
    """Crawl a single site and return raw data."""
    try:
        from aat.core.models import EngineConfig
        from aat.engine.web import WebEngine
        from app.crawler import (
            _extract_page_data,
            _observe_interactions,
            _detect_features,
        )
    except ImportError as exc:
        logger.error("Import failed: %s", exc)
        return None

    engine_config = EngineConfig(
        type="web", headless=True,
        viewport_width=1920, viewport_height=1080,
    )
    engine = WebEngine(engine_config)

    try:
        await engine.start()
        page = engine.page
        await page.set_extra_http_headers(
            {"ngrok-skip-browser-warning": "true"}
        )

        logger.info("[%s] Navigating to %s", name, url)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        except Exception as nav_exc:
            logger.warning("[%s] Navigation failed: %s", name, nav_exc)
            return None

        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

        # Extract page data
        pdata = await _extract_page_data(page, url, take_screenshot=False)
        pages_list = [pdata]

        # Detect features
        page_text = await page.inner_text("body")
        feature_list = await _detect_features(page, page_text, pdata)
        features = {f["feature"]: f for f in feature_list}

        # Observe interactions (limited)
        observations = await _observe_interactions(
            page, pdata, url, max_interactions=8,
        )

        logger.info(
            "[%s] Crawled: %d forms, %d buttons, %d nav items, %d observations, features=%s",
            name,
            len(pdata.get("forms", [])),
            len(pdata.get("buttons", [])),
            sum(len(m.get("items", [])) for m in pdata.get("nav_menus", [])),
            len(observations),
            list(features.keys())[:5],
        )

        return {
            "pages": pages_list,
            "observations": observations,
            "detected_features": list(features.keys()),
            "summary": {
                "total_pages": 1,
                "site_type": {"type": "unknown", "confidence": 0.0},
            },
            "broken_links": [],
        }

    except Exception as exc:
        logger.error("[%s] Crawl failed: %s", name, exc)
        return None
    finally:
        try:
            await engine.stop()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Generate plans
# ---------------------------------------------------------------------------

def generate_default(crawl_data: dict, site_url: str) -> dict:
    """Generate a default plan (no AI)."""
    from app.routers.scan import _generate_default_plan

    # Create a minimal scan-like object
    class FakeScan:
        target_url = site_url

    return _generate_default_plan(
        FakeScan(),
        crawl_data["pages"],
        crawl_data["broken_links"],
        crawl_data["detected_features"],
        crawl_data["summary"],
        "en",
        crawl_data["observations"],
    )


async def generate_ai_plan(crawl_data: dict, site_url: str) -> dict | None:
    """Generate an AI plan."""
    from app.routers.scan import (
        _PLAN_SYSTEM,
        _PLAN_USER,
        _ai_raw_call,
        _extract_json,
    )
    from app.scenario_utils import (
        compress_crawl_data,
        compress_observations_for_ai,
    )
    from app.test_patterns import (
        build_pattern_summary,
        match_elements_to_patterns,
    )
    from app.routers.scan import BUSINESS_TEMPLATES

    pages = crawl_data["pages"]
    features = crawl_data["detected_features"]
    observations = crawl_data["observations"]
    summary = crawl_data["summary"]

    # Collect elements
    nav_menus = []
    forms = []
    buttons = []
    links_sample = []
    for p in pages:
        nav_menus.extend(p.get("nav_menus", []))
        forms.extend(p.get("forms", []))
        buttons.extend(p.get("buttons", []))
        for link in p.get("links", [])[:10]:
            links_sample.append({
                "text": link.get("text", ""),
                "href": link.get("href", ""),
            })

    site_type_info = summary.get("site_type") or {}
    site_type_name = (
        site_type_info.get("type", "unknown")
        if isinstance(site_type_info, dict) else "unknown"
    )
    site_type_conf = (
        site_type_info.get("confidence", 0.0)
        if isinstance(site_type_info, dict) else 0.0
    )

    # Business hints
    business_hints_lines = []
    for st in [site_type_name] + [
        k for k in BUSINESS_TEMPLATES if k != site_type_name
    ]:
        for tmpl in BUSINESS_TEMPLATES.get(st, []):
            req_feat = tmpl.get("requires_feature", "")
            if req_feat and req_feat not in features:
                continue
            name = tmpl.get("name_en", "")
            desc = tmpl.get("desc_en", "")
            business_hints_lines.append(f"- {name}: {desc}")
    business_hints = (
        "\n".join(business_hints_lines)
        if business_hints_lines
        else "No specific business tests for this site type."
    )

    # Special instructions
    special_parts: list[str] = []
    if "spa" in features:
        special_parts.append("SPA SITE DETECTED: Assert text_visible, not URL changes.")
    matched_patterns = match_elements_to_patterns(pages, observations)
    pattern_hint = build_pattern_summary(matched_patterns)
    if pattern_hint:
        special_parts.append(pattern_hint)

    plan_crawl = {
        "nav_menus": nav_menus,
        "forms": forms,
        "buttons": buttons,
        "links": links_sample,
    }

    def _trunc_json(obj: Any, limit: int = 3000) -> str:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
        return s[:limit] if len(s) > limit else s

    plan_user = _PLAN_USER.format(
        language="English",
        target_url=site_url,
        total_pages=summary.get("total_pages", len(pages)),
        detected_features=", ".join(features) if features else "none",
        site_type=site_type_name,
        site_type_confidence=f"{site_type_conf:.0%}",
        crawl_data=compress_crawl_data(plan_crawl, max_chars=9000),
        broken_links_json=_trunc_json([]),
        broken_count=0,
        observations_json=(
            compress_observations_for_ai(observations, max_tokens=6000)
            if observations
            else "No observations collected."
        ),
        business_hints=business_hints,
        reference_documents="No reference documents provided.",
        special_instructions="\n\n".join(special_parts) if special_parts else "",
    )

    # Create adapter
    from aat.adapters import ADAPTER_REGISTRY
    from aat.core.models import AIConfig
    from app.config import settings

    ai_config = AIConfig(
        provider=settings.ai_provider,
        api_key=settings.ai_api_key,
        model="gpt-4o-mini",
    )
    adapter_cls = ADAPTER_REGISTRY.get(ai_config.provider)
    if adapter_cls is None:
        logger.error("No adapter for provider: %s", ai_config.provider)
        return None

    adapter = adapter_cls(ai_config)

    try:
        raw = await _ai_raw_call(adapter, plan_user, system_prompt=_PLAN_SYSTEM)
        plan = _extract_json(raw)
        return plan
    except Exception as exc:
        logger.error("AI plan generation failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def extract_tests(plan: dict) -> list[dict]:
    """Flatten all tests from a plan."""
    tests = []
    for cat in plan.get("categories", []):
        cat_id = cat.get("id", "?")
        for t in cat.get("tests", []):
            tests.append({
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "category": cat_id,
                "priority": t.get("priority", "medium"),
                "requires_auth": t.get("requires_auth", False),
            })
    return tests


def extract_categories(plan: dict) -> set[str]:
    return {cat.get("id", "?") for cat in plan.get("categories", [])}


def compare_plans(
    ai_plan: dict | None,
    default_plan: dict,
    site_name: str,
) -> dict:
    """Compare AI plan vs default plan."""
    default_tests = extract_tests(default_plan)
    default_names = {t["name"].lower().strip() for t in default_tests}
    default_cats = extract_categories(default_plan)

    result = {
        "site": site_name,
        "default_count": len(default_tests),
        "default_categories": sorted(default_cats),
        "default_tests": [t["name"] for t in default_tests],
    }

    if ai_plan is None:
        result["ai_count"] = "FAILED"
        result["ai_categories"] = []
        result["ai_only"] = []
        result["default_only"] = []
        result["notes"] = "AI plan generation failed"
        return result

    ai_tests = extract_tests(ai_plan)
    ai_names = {t["name"].lower().strip() for t in ai_tests}
    ai_cats = extract_categories(ai_plan)

    # Find unique items (fuzzy by checking substring overlap)
    ai_only = []
    for t in ai_tests:
        name_l = t["name"].lower().strip()
        # Check if any default test has significant overlap
        matched = False
        for dn in default_names:
            # Simple overlap check
            words_ai = set(name_l.split())
            words_def = set(dn.split())
            if words_ai & words_def and len(words_ai & words_def) >= max(1, len(words_ai) // 2):
                matched = True
                break
        if not matched:
            ai_only.append(t["name"])

    default_only = []
    for t in default_tests:
        name_l = t["name"].lower().strip()
        matched = False
        for an in ai_names:
            words_def = set(name_l.split())
            words_ai = set(an.split())
            if words_def & words_ai and len(words_def & words_ai) >= max(1, len(words_def) // 2):
                matched = True
                break
        if not matched:
            default_only.append(t["name"])

    result["ai_count"] = len(ai_tests)
    result["ai_categories"] = sorted(ai_cats)
    result["ai_tests"] = [t["name"] for t in ai_tests]
    result["ai_only"] = ai_only
    result["default_only"] = default_only
    result["notes"] = ""

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_ab_test() -> list[dict]:
    """Run the full A/B test across all accessible sites."""
    results: list[dict] = []
    skipped: list[str] = []

    # First try existing fixtures
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    fixture_map: dict[str, str] = {}
    if os.path.isdir(fixtures_dir):
        for fname in os.listdir(fixtures_dir):
            if fname.endswith(".json"):
                fixture_map[fname.replace(".json", "")] = os.path.join(
                    fixtures_dir, fname,
                )

    for site in TEST_SITES:
        url = site["url"]
        name = site["name"]
        site_type = site["type"]

        logger.info("=" * 60)
        logger.info("Processing: %s (%s)", name, url)
        logger.info("=" * 60)

        # Try fixture first
        fixture_name = name.lower().replace(" ", "_")
        crawl_data = None

        # Check known fixture mappings
        fixture_aliases = {
            "saucedemo": "saucedemo",
            "demoqa": "demoqa",
            "theinternet": "the_internet",
            "expandtest": "expand_testing",
        }
        fixture_key = fixture_aliases.get(fixture_name)
        if fixture_key and fixture_key in fixture_map:
            logger.info("[%s] Using fixture: %s", name, fixture_key)
            with open(fixture_map[fixture_key]) as f:
                raw = json.load(f)
            crawl_data = {
                "pages": raw.get("pages", []),
                "observations": raw.get("observations", []),
                "detected_features": raw.get("detected_features", []),
                "summary": {
                    "total_pages": len(raw.get("pages", [])),
                    "site_type": {"type": "unknown", "confidence": 0.0},
                },
                "broken_links": [],
            }

        # Otherwise crawl live
        if crawl_data is None:
            crawl_data = await crawl_one(url, name)
            if crawl_data is None:
                logger.warning("[%s] SKIPPED — site unreachable", name)
                skipped.append(name)
                continue

        # Generate default plan
        logger.info("[%s] Generating default plan...", name)
        default_plan = generate_default(crawl_data, url)
        default_tests = extract_tests(default_plan)
        logger.info(
            "[%s] Default: %d tests in %s",
            name, len(default_tests),
            sorted(extract_categories(default_plan)),
        )

        # Generate AI plan
        logger.info("[%s] Generating AI plan...", name)
        t0 = time.monotonic()
        ai_plan = await generate_ai_plan(crawl_data, url)
        elapsed = time.monotonic() - t0
        if ai_plan:
            ai_tests = extract_tests(ai_plan)
            logger.info(
                "[%s] AI: %d tests in %s (%.1fs)",
                name, len(ai_tests),
                sorted(extract_categories(ai_plan)),
                elapsed,
            )
        else:
            logger.warning("[%s] AI plan FAILED (%.1fs)", name, elapsed)

        # Compare
        comparison = compare_plans(ai_plan, default_plan, name)
        comparison["site_type"] = site_type
        results.append(comparison)

        # Brief delay to avoid rate limiting
        await asyncio.sleep(1)

    if skipped:
        logger.info("Skipped sites: %s", ", ".join(skipped))

    return results


def print_results(results: list[dict]) -> None:
    """Print comparison table and analysis."""
    print("\n" + "=" * 100)
    print("A/B TEST RESULTS: AI Plan vs Default Plan")
    print("=" * 100)

    # Header
    print(f"\n{'Site':<18} {'Type':<12} {'AI#':<6} {'Def#':<6} "
          f"{'AI-only':<30} {'Def-only':<30} {'Notes'}")
    print("-" * 130)

    total_ai = 0
    total_default = 0
    ai_only_all: list[str] = []
    default_only_all: list[str] = []
    failed_count = 0

    for r in results:
        ai_count = r["ai_count"]
        def_count = r["default_count"]

        ai_only_str = ", ".join(r["ai_only"][:3]) or "-"
        if len(r["ai_only"]) > 3:
            ai_only_str += f" +{len(r['ai_only']) - 3}"
        def_only_str = ", ".join(r["default_only"][:3]) or "-"
        if len(r["default_only"]) > 3:
            def_only_str += f" +{len(r['default_only']) - 3}"

        if ai_only_str == "-":
            ai_only_str = "(none)"
        if def_only_str == "-":
            def_only_str = "(none)"

        ai_str = str(ai_count) if isinstance(ai_count, int) else ai_count

        print(f"{r['site']:<18} {r.get('site_type', '?'):<12} "
              f"{ai_str:<6} {def_count:<6} "
              f"{ai_only_str:<30} {def_only_str:<30} "
              f"{r.get('notes', '')}")

        if isinstance(ai_count, int):
            total_ai += ai_count
            total_default += def_count
            ai_only_all.extend(r["ai_only"])
            default_only_all.extend(r["default_only"])
        else:
            failed_count += 1

    print("-" * 130)

    # Summary
    valid = len(results) - failed_count
    print(f"\nSites tested: {len(results)} ({failed_count} AI failures)")
    print(f"Total AI tests: {total_ai}, Total Default tests: {total_default}")

    if total_ai > 0:
        coverage = total_default / total_ai * 100
        print(f"Default coverage of AI: {coverage:.1f}%")
    else:
        coverage = 0

    print(f"\nAI-only items ({len(ai_only_all)} total):")
    for item in ai_only_all[:20]:
        print(f"  - {item}")

    print(f"\nDefault-only items ({len(default_only_all)} total):")
    for item in default_only_all[:20]:
        print(f"  - {item}")

    # Per-site detail
    print("\n" + "=" * 80)
    print("DETAILED PER-SITE COMPARISON")
    print("=" * 80)
    for r in results:
        print(f"\n--- {r['site']} ({r.get('site_type', '?')}) ---")
        print(f"  AI categories:      {r.get('ai_categories', [])}")
        print(f"  Default categories: {r['default_categories']}")
        if r.get("ai_tests"):
            print(f"  AI tests:")
            for t in r["ai_tests"]:
                marker = " [UNIQUE]" if t in r.get("ai_only", []) else ""
                print(f"    - {t}{marker}")
        print(f"  Default tests:")
        for t in r["default_tests"]:
            marker = " [UNIQUE]" if t in r.get("default_only", []) else ""
            print(f"    - {t}{marker}")

    # Verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)
    if coverage >= 90:
        print(f"Default covers {coverage:.1f}% of AI output.")
        print("RECOMMENDATION: REMOVE AI plan generation (2단계 AI 제거 확정)")
    elif coverage >= 80:
        print(f"Default covers {coverage:.1f}% of AI output.")
        print("RECOMMENDATION: Keep AI as 'advanced mode' option")
    else:
        print(f"Default covers only {coverage:.1f}% of AI output.")
        print("RECOMMENDATION: Keep AI, optimize prompts only")


async def main():
    results = await run_ab_test()
    print_results(results)

    # Save raw results
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "plan_ab_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nRaw results saved to: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
