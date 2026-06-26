"""
════════════════════════════════════════════════════════════════════════════════
                    📸 Baseline Screenshot Storage Manager
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Manages persistent storage of baseline screenshots for visual regression testing.
Provides disk-backed storage with metadata tracking, multi-viewport support,
and CRUD operations for baseline lifecycle management in the AAT system.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Create a new baseline from test execution screenshots
store = BaselineStore(data_dir=Path(".aat/data"))
baseline_meta = store.save(
    scenario_id="login_flow_001",
    screenshot_paths={1: Path("screenshots/step1_after.png")},
    scenario_name="User Login Flow",
    url="https://example.com/login",
    viewport="desktop"
)

# Later: retrieve baseline for comparison
baseline_images = store.load("login_flow_001", viewport="desktop")
for step_num, img_path in baseline_images.items():
    compare_with_current_run(img_path)
```

⚙️  CORE ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
    BaselineStore
         ├── save()      → Store screenshots + metadata as baseline
         ├── load()      → Retrieve baseline images by scenario + viewport
         ├── load_meta() → Fetch baseline metadata (no images)
         ├── exists()    → Check if baseline exists
         ├── clear()     → Delete single baseline
         └── clear_all() → Delete all baselines (bulk cleanup)

    Storage Layout:
    {data_dir}/baselines/
      ├── login_flow_001/
      │   ├── meta.json
      │   ├── step001_after.png
      │   ├── step002_after.png
      │   └── step001-mobile_after.png    (viewport variant)
      ├── checkout_flow_002/
      │   ├── meta.json
      │   └── step001_after.png
      └── ...

    Multi-Viewport File Naming:
    No viewport:     step001_after.png
    With viewport:   step001-{viewport}_after.png
    Example:        step001-mobile_after.png, step001-tablet_after.png

    Save Flow:
    ┌─────────────────────────────────────────────────────────────────┐
    │ Input: scenario_id, screenshot_paths, metadata                 │
    │                         ↓                                        │
    │ 1. Create scenario directory: {data_dir}/baselines/{scenario_id}/│
    │                         ↓                                        │
    │ 2. Copy screenshot files with viewport suffix (if provided)      │
    │                         ↓                                        │
    │ 3. Generate metadata (timestamp, step count, URL, etc.)          │
    │                         ↓                                        │
    │ 4. Write meta.json for later reference                         │
    │                         ↓                                        │
    │ 5. Return BaselineMeta object                                  │
    └─────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- Baseline Creation: Save step screenshots as reference images with metadata
- Viewport Support: Store multiple viewport variants (mobile, tablet, desktop)
- Metadata Tracking: Captures scenario details, timestamp, URL, step count
- Baseline Retrieval: Load images by scenario ID and optional viewport filter
- Existence Checking: Verify if baseline exists without loading files
- Bulk Operations: List all baselines, clear individual or all baselines
- Safe Overwrites: Preserves viewport variants when overwriting main baseline

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Only supports PNG format (hardcoded in file naming pattern)
- No built-in image compression or optimization
- Baseline deletion is permanent (no undo/restore mechanism)
- Concurrent writes to same scenario_id can cause race conditions
- No schema validation for metadata (relies on Pydantic BaselineMeta model)
- File operations are synchronous (not async)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Create separate baselines for each viewport configuration
- Include viewport label when testing responsive designs
- Use consistent scenario naming (lowercase, underscores, descriptive)
- Archive old baselines before major UI overhauls
- Commit baselines to version control for reproducible regression tests
- Use meta.json for baseline version tracking and migration

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Establishing visual baselines for new test scenarios
✅ Comparing current runs against approved reference states
✅ Multi-viewport testing (mobile, tablet, desktop)
✅ Visual regression workflows with diff generation
❌ Don't use for temporary storage (use in-memory caches instead)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from aat.core import BaselineMeta

logger = logging.getLogger(__name__)


class BaselineStore:
    """Manages baseline screenshots on disk.

    Storage layout::

        {data_dir}/baselines/{scenario_id}/
            meta.json
            step001_after.png
            step002_after.png
            ...
    """

    def __init__(self, data_dir: Path) -> None:
        self._root = data_dir / "baselines"
        self._root.mkdir(parents=True, exist_ok=True)

    # -- write ---------------------------------------------------------------

    def save(
        self,
        scenario_id: str,
        screenshot_paths: dict[int, Path],
        *,
        scenario_name: str = "",
        url: str = "",
        viewport: str = "",
    ) -> BaselineMeta:
        """Save step screenshots as the baseline for *scenario_id*.

        Args:
            scenario_id: Unique scenario identifier.
            screenshot_paths: Mapping of step number → screenshot file path.
            scenario_name: Human-readable name (stored in meta).
            url: Target URL at capture time.
            viewport: Viewport label (e.g. "mobile", "tablet", "desktop").
                      If set, filenames use ``step001-mobile_after.png`` pattern.

        Returns:
            Metadata describing the saved baseline.
        """
        dest = self._root / scenario_id
        # Only wipe the directory if no viewport suffix (full overwrite)
        # With viewport, we preserve other viewport files
        if not viewport and dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)

        suffix = f"-{viewport}" if viewport else ""
        for step_num, src in sorted(screenshot_paths.items()):
            src_path = Path(src)
            if src_path.exists():
                target = dest / f"step{step_num:03d}{suffix}_after.png"
                shutil.copy2(src_path, target)

        meta = BaselineMeta(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            url=url,
            step_count=len(screenshot_paths),
            captured_at=datetime.now(),
        )
        (dest / "meta.json").write_text(meta.model_dump_json(indent=2), encoding="utf-8")
        return meta

    # -- read ----------------------------------------------------------------

    def load(self, scenario_id: str, *, viewport: str = "") -> dict[int, Path]:
        """Load baseline screenshots for *scenario_id*.

        Args:
            scenario_id: Scenario identifier.
            viewport: Viewport label to filter by (e.g. "mobile").
                      Empty string loads the default (no-suffix) files.

        Returns:
            Mapping of step number → baseline PNG path.
        """
        dest = self._root / scenario_id
        if not dest.exists():
            return {}

        suffix = f"-{viewport}" if viewport else ""
        pattern = f"step*{suffix}_after.png"

        result: dict[int, Path] = {}
        for png in sorted(dest.glob(pattern)):
            # step001_after.png → 1  or  step001-mobile_after.png → 1
            try:
                stem = png.name.split("_")[0]  # "step001" or "step001-mobile"
                num_str = stem.split("-")[0].replace("step", "")
                num = int(num_str)
                result[num] = png
            except (ValueError, IndexError):
                continue
        return result

    def load_meta(self, scenario_id: str) -> BaselineMeta | None:
        """Load metadata for a baseline."""
        meta_path = self._root / scenario_id / "meta.json"
        if not meta_path.exists():
            return None
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return BaselineMeta(**data)

    def exists(self, scenario_id: str) -> bool:
        return (self._root / scenario_id / "meta.json").exists()

    # -- list / delete -------------------------------------------------------

    def list_all(self) -> list[BaselineMeta]:
        """List all saved baselines."""
        results: list[BaselineMeta] = []
        for meta_path in sorted(self._root.glob("*/meta.json")):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                results.append(BaselineMeta(**data))
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to load baseline metadata from %s: %s", meta_path, e)
                continue
        return results

    def clear(self, scenario_id: str) -> bool:
        """Delete baseline for *scenario_id*. Returns True if it existed."""
        dest = self._root / scenario_id
        if dest.exists():
            shutil.rmtree(dest)
            return True
        return False

    def clear_all(self) -> int:
        """Delete all baselines. Returns count of removed baselines."""
        count = 0
        for child in self._root.iterdir():
            if child.is_dir() and (child / "meta.json").exists():
                shutil.rmtree(child)
                count += 1
        return count
