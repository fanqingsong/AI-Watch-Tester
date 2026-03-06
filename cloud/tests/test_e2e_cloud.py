"""E2E Cloud Scenario Generation Test.

Tests the full AI scenario generation pipeline (adapter -> post-processing)
using real AI API calls against fixture scan data.

Requires OPENAI_API_KEY (or AWT_AI_API_KEY) environment variable.
Skips gracefully when no API key is available.

Usage:
    # All sites, single generation
    pytest cloud/tests/test_e2e_cloud.py -k test_single_generation -v -s

    # Specific site only
    pytest cloud/tests/test_e2e_cloud.py -k "test_single_generation[saucedemo]" -v -s

    # Stability (expensive — single fixture, 5 AI calls)
    pytest cloud/tests/test_e2e_cloud.py -k test_stability_5_runs -v -s

    # Post-processing diff for all sites
    pytest cloud/tests/test_e2e_cloud.py -k test_postprocessing_fixes -v -s
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
# Path setup -- ensure cloud/app and src/ are importable
# ---------------------------------------------------------------------------
_CLOUD_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CLOUD_DIR.parent
sys.path.insert(0, str(_CLOUD_DIR))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

# Load cloud/.env so AWT_AI_API_KEY is available
_ENV_FILE = _CLOUD_DIR / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

from app.routers.scan import (  # noqa: E402
    _EXECUTE_SYSTEM,
    _EXECUTE_USER,
    _build_observation_table,
    _chunk_tests,
)
from app.scenario_utils import (  # noqa: E402
    DEFAULT_AI_MODELS,
    ensure_post_submit_assert,
    fix_field_targets,
    fix_form_submit_steps,
    inject_login_prefix,
    validate_and_retry,
)

from aat.adapters import ADAPTER_REGISTRY  # noqa: E402
from aat.core.models import AIConfig, Scenario  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# Auto-discover all fixture JSON files (sorted alphabetically by stem)
ALL_FIXTURES = sorted(p.stem for p in FIXTURE_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_api_key() -> str | None:
    """Get API key from environment variables."""
    return (
        os.environ.get("AWT_AI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or None
    )


def load_fixture(name: str = "sample_scan_data") -> dict[str, Any]:
    """Load a fixture JSON file by name (without .json extension)."""
    path = FIXTURE_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def create_adapter() -> Any:
    """Create an AI adapter from environment variables.

    Supports OPENAI_API_KEY -> OpenAIAdapter.
    """
    api_key = _get_api_key()
    if not api_key:
        pytest.skip("No API key set (OPENAI_API_KEY or AWT_AI_API_KEY)")

    provider = os.environ.get("AWT_AI_PROVIDER", "openai")
    model = DEFAULT_AI_MODELS.get(provider, "gpt-4o-mini")

    config = AIConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        max_tokens=16000,
        temperature=0.3,
    )

    adapter_cls = ADAPTER_REGISTRY.get(provider)
    if not adapter_cls:
        pytest.skip(f"Unknown provider: {provider}")

    return adapter_cls(config)


def _build_prompt(
    fixture: dict[str, Any],
    batch: list[dict],
) -> str:
    """Build the _EXECUTE_USER prompt for a batch of tests."""
    observations = fixture.get("observations", [])
    pages = fixture.get("pages", [])
    target_url = fixture["target_url"]
    auth_data = fixture.get("auth_data", {})
    test_data = fixture.get("test_data", {})

    observation_table = _build_observation_table(observations)
    crawl_str = json.dumps(pages, ensure_ascii=False, indent=2)[:4000]
    user_data = {**auth_data, **test_data}
    user_data_str = json.dumps(user_data, ensure_ascii=False, indent=2)

    return _EXECUTE_USER.format(
        target_url=target_url,
        crawl_data=crawl_str,
        observation_table=observation_table,
        selected_tests=json.dumps(batch, ensure_ascii=False, indent=2),
        user_data=user_data_str,
        extra_instructions="",
        reference_documents="",
        batch_count=len(batch),
        language_instruction="",
    )


async def generate_raw(fixture: dict[str, Any]) -> list[Scenario]:
    """Batch AI calls only (no post-processing)."""
    adapter = create_adapter()
    selected = fixture["selected_tests"]
    batches = _chunk_tests(selected, batch_size=3)

    all_scenarios: list[Scenario] = []
    for batch_idx, batch in enumerate(batches):
        prompt = _build_prompt(fixture, batch)
        logger.info(
            "Calling AI for batch %d/%d (%d tests)...",
            batch_idx + 1, len(batches), len(batch),
        )
        scenarios = await adapter.generate_scenarios(
            prompt, system_prompt=_EXECUTE_SYSTEM,
        )
        all_scenarios.extend(scenarios)

    # Renumber SC-IDs sequentially
    for i, sc in enumerate(all_scenarios, 1):
        if hasattr(sc, "id"):
            sc.__dict__["id"] = f"SC-{i:03d}"

    return all_scenarios


def apply_postprocessing(
    scenarios: list[Scenario],
    fixture: dict[str, Any],
) -> list[Scenario]:
    """Apply the same post-processing pipeline as scan.py."""
    observations = fixture.get("observations", [])
    auth_data = fixture.get("auth_data", {})
    target_url = fixture["target_url"]

    scenarios = fix_field_targets(scenarios, observations)
    scenarios = fix_form_submit_steps(scenarios, observations)
    scenarios = ensure_post_submit_assert(scenarios)
    scenarios = inject_login_prefix(
        scenarios, observations, auth_data, target_url=target_url,
    )
    return scenarios


async def generate_and_postprocess(
    fixture: dict[str, Any],
) -> tuple[list[Scenario], list[Scenario]]:
    """Full pipeline: generate_raw + apply_postprocessing.

    Returns (raw_scenarios, postprocessed_scenarios).
    """
    raw = await generate_raw(fixture)
    # Deep copy raw for comparison
    raw_dicts = [
        s.model_dump(mode="json", exclude_none=True) for s in raw
    ]
    raw_copy = [Scenario.model_validate(d) for d in raw_dicts]

    processed = apply_postprocessing(list(raw), fixture)

    # Validate + retry (async)
    adapter = create_adapter()
    prompt = _build_prompt(fixture, fixture["selected_tests"])
    observations = fixture.get("observations", [])
    pages = fixture.get("pages", [])
    processed, _validation = await validate_and_retry(
        processed, observations, pages, adapter, prompt,
        system_prompt=_EXECUTE_SYSTEM,
    )

    return raw_copy, processed


def validate_structure(scenarios: list[Scenario]) -> list[str]:
    """Validate scenario structure, return list of error messages."""
    errors: list[str] = []

    if not scenarios:
        errors.append("No scenarios generated")
        return errors

    seen_ids: set[str] = set()
    for i, sc in enumerate(scenarios):
        # SC-ID format
        if not sc.id.startswith("SC-"):
            errors.append(
                f"Scenario {i}: invalid ID format '{sc.id}'"
            )
        if sc.id in seen_ids:
            errors.append(f"Scenario {i}: duplicate ID '{sc.id}'")
        seen_ids.add(sc.id)

        # Must have steps
        if not sc.steps:
            errors.append(f"{sc.id}: no steps")
            continue

        # First step should be navigate
        first_action = sc.steps[0].action.value
        if first_action != "navigate":
            errors.append(
                f"{sc.id}: first step is '{first_action}', "
                f"expected 'navigate'"
            )

        # Step numbering should be sequential
        for j, step in enumerate(sc.steps):
            expected_num = j + 1
            if step.step != expected_num:
                errors.append(
                    f"{sc.id} step {j}: number is {step.step}, "
                    f"expected {expected_num}"
                )

    return errors


def save_yaml(scenarios: list[Scenario], filename: str) -> Path:
    """Save scenarios as YAML to output/ directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename

    scenario_dicts = [
        s.model_dump(mode="json", exclude_none=True)
        for s in scenarios
    ]
    yaml_str = yaml.safe_dump(
        scenario_dicts,
        default_flow_style=False,
        allow_unicode=True,
    )
    path.write_text(yaml_str, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestE2EScenarioGeneration:
    """E2E tests for the AI scenario generation pipeline."""

    @pytest.fixture(autouse=True)
    def _skip_without_key(self) -> None:
        if not _get_api_key():
            pytest.skip(
                "No API key (OPENAI_API_KEY or AWT_AI_API_KEY)"
            )

    @pytest.mark.parametrize("site", ALL_FIXTURES)
    def test_single_generation(self, site: str) -> None:
        """Single AI call + full post-processing, structure check."""
        fixture = load_fixture(site)
        selected_count = len(fixture["selected_tests"])

        raw, processed = asyncio.run(
            generate_and_postprocess(fixture),
        )

        # --- Structure validation ---
        errors = validate_structure(processed)
        if errors:
            print(f"\n=== STRUCTURE ERRORS [{site}] ===")
            for e in errors:
                print(f"  - {e}")

        assert not errors, f"[{site}] Structure validation failed: {errors}"

        # Scenario count should match selected tests
        assert len(processed) >= selected_count, (
            f"[{site}] Expected >= {selected_count} scenarios, "
            f"got {len(processed)}"
        )

        # SC-IDs should be sequential
        for i, sc in enumerate(processed, 1):
            expected_id = f"SC-{i:03d}"
            assert sc.id == expected_id, (
                f"[{site}] Expected {expected_id}, got {sc.id}"
            )

        # YAML serialization should work
        path = save_yaml(processed, f"{site}_run_single.yaml")
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(loaded, list)
        assert len(loaded) == len(processed)

        total_steps = sum(len(s.steps) for s in processed)
        print(f"\n=== SINGLE GENERATION RESULT [{site}] ===")
        print(f"  URL: {fixture['target_url']}")
        print(f"  Selected tests: {selected_count}")
        print(f"  Generated scenarios: {len(processed)}")
        print(f"  Total steps: {total_steps}")
        print(f"  Saved to: {path}")

    def test_stability_5_runs(self) -> None:
        """5 repeated runs, check consistency.

        Uses sample_scan_data fixture by default.
        Override with --site env var: FIXTURE_NAME=saucedemo
        """
        site = os.environ.get("FIXTURE_NAME", "sample_scan_data")
        fixture = load_fixture(site)
        num_runs = 5

        results: list[dict[str, Any]] = []
        passed = 0
        scenario_counts: list[int] = []

        for run_idx in range(1, num_runs + 1):
            print(f"\n--- Run {run_idx}/{num_runs} [{site}] ---")
            try:
                _raw, processed = asyncio.run(
                    generate_and_postprocess(fixture),
                )
                errors = validate_structure(processed)
                count = len(processed)
                scenario_counts.append(count)

                name = f"{site}_run_{run_idx:03d}.yaml"
                save_yaml(processed, name)

                if errors:
                    results.append({
                        "run": run_idx, "status": "FAIL",
                        "errors": errors, "count": count,
                    })
                    print(
                        f"  FAIL: {len(errors)} errors, "
                        f"{count} scenarios"
                    )
                else:
                    results.append({
                        "run": run_idx, "status": "PASS",
                        "errors": [], "count": count,
                    })
                    passed += 1
                    print(f"  PASS: {count} scenarios ({name})")

            except Exception as exc:
                results.append({
                    "run": run_idx, "status": "ERROR",
                    "errors": [str(exc)], "count": 0,
                })
                print(f"  ERROR: {exc}")

        # --- Report ---
        header = (
            f"STABILITY REPORT [{site}] ({passed}/{num_runs} passed)"
        )
        print(f"\n=== {header} ===")
        for r in results:
            status = r["status"]
            count = r["count"]
            errs = r["errors"]
            suffix = f" -- {errs}" if errs else ""
            print(
                f"  Run {r['run']}: {status} "
                f"({count} scenarios){suffix}"
            )

        if scenario_counts:
            print(f"  Scenario counts: {scenario_counts}")
            if len(set(scenario_counts)) > 1:
                print("  WARNING: Inconsistent counts!")

        if passed < num_runs:
            print(f"\n  UNSTABLE: {passed}/{num_runs} passed")

        assert passed == num_runs, (
            f"Stability [{site}]: {passed}/{num_runs} passed"
        )

    @pytest.mark.parametrize("site", ALL_FIXTURES)
    def test_postprocessing_fixes(self, site: str) -> None:
        """Compare raw AI output vs post-processed output."""
        fixture = load_fixture(site)

        raw, processed = asyncio.run(
            generate_and_postprocess(fixture),
        )

        # Count differences
        raw_steps = sum(len(s.steps) for s in raw)
        proc_steps = sum(len(s.steps) for s in processed)

        raw_asserts = sum(
            1 for s in raw for step in s.steps
            if step.action.value == "assert"
        )
        proc_asserts = sum(
            1 for s in processed for step in s.steps
            if step.action.value == "assert"
        )

        # Count targets
        raw_targets: list[str] = []
        proc_targets: list[str] = []
        for s in raw:
            for step in s.steps:
                if step.target:
                    t = step.target
                    raw_targets.append(
                        str(t.text or t.selector or "")
                    )
        for s in processed:
            for step in s.steps:
                if step.target:
                    t = step.target
                    proc_targets.append(
                        str(t.text or t.selector or "")
                    )

        print(f"\n=== POST-PROCESSING DIFF [{site}] ===")
        print(
            f"  Raw scenarios: {len(raw)}, "
            f"Processed: {len(processed)}"
        )
        print(f"  Raw steps: {raw_steps}, Processed: {proc_steps}")
        print(f"  Steps added: {proc_steps - raw_steps}")
        print(
            f"  Raw asserts: {raw_asserts}, "
            f"Processed: {proc_asserts}"
        )
        print(f"  Asserts added: {proc_asserts - raw_asserts}")
        print(
            f"  Raw targets: {len(raw_targets)}, "
            f"Processed: {len(proc_targets)}"
        )

        # Save both for manual inspection
        save_yaml(raw, f"{site}_postproc_raw.yaml")
        save_yaml(processed, f"{site}_postproc_fixed.yaml")
        print(
            f"  Saved: {site}_postproc_raw.yaml, "
            f"{site}_postproc_fixed.yaml"
        )

        # Post-processing should not reduce scenarios
        assert len(processed) >= len(raw), (
            f"[{site}] Post-processing reduced scenarios: "
            f"{len(raw)} -> {len(processed)}"
        )

        # Structure should be valid after processing
        errors = validate_structure(processed)
        assert not errors, (
            f"[{site}] Post-processed structure invalid: {errors}"
        )
