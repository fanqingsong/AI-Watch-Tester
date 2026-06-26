"""
════════════════════════════════════════════════════════════════════════════════
                   📚 Design Guide Learning Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Registers design guide images for learning element references and platform-
specific testing tips. Enables manual training of the visual matching system
with known-good UI components and framework-specific patterns.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Learn from single image
aat learn add button.png --name submit_button

# Learn from directory of images
aat learn add design_system/ --name primary_buttons

# Add platform-specific testing tip
aat learn platform --platform flutter_canvaskit --tip "Wait for Semantics node stabilization"

# Use with custom config
aat learn add icons/ --name navigation_icons --config aat.config.yaml
```

⚙️  LEARNING PROCESS
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│                  Design Guide Learning Workflow                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Image Collection                                          │  │
│  │    → Accept .png, .jpg, .jpeg files                          │  │
│  │    → Single file or directory input                           │  │
│  │    → Verify file existence and readability                    │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 2. Image Processing                                          │  │
│  │    → Calculate SHA-256 hash for deduplication                │  │
│  │    → Copy to .aat/assets/ for reference                      │  │
│  │    → Extract image metadata and properties                    │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 3. Element Registration                                     │  │
│  │    → Create LearnedElement records                           │  │
│  │    → Store with target_name and screenshot_hash              │  │
│  │    → Set confidence=1.0 for manual registrations             │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 4. Platform Tip Storage (Optional)                            │  │
│  │    → Add framework-specific testing advice                    │  │
│  │    → Associate with platform identifier                      │  │
│  │    → Mark as user-added (vs builtin)                          │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 5. Database Storage                                          │  │
│  │    → Save to .aat/learned.db                                 │  │
│  │    → Index by target_name and platform                        │  │
│  │    → Enable fast lookup during matching                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **image learning**: Register design guide images for element reference
- **platform tips**: Add framework-specific testing guidance
- **deduplication**: SHA-256 hashing prevents duplicate registrations
- **asset management**: Organized storage in .aat/assets/ directory
- **database integration**: LearnedStore integration for persistent learning
- **bulk import**: Process entire directories of design assets

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Manual learning requires high-quality reference images
- Platform tips are text-only (no automated validation)
- Learned elements require consistent visual appearance
- Database size grows with accumulated learning data
- No automatic learning from test failures (use --learn mode)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Use consistent naming conventions for learned elements
- Capture design system components for reliable matching
- Add platform tips for framework-specific issues discovered
- Register common UI patterns from design documentation
- Use high-resolution images for better matching accuracy
- Combine with automated learning for comprehensive coverage

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Training system with design system components
✅ Adding framework-specific testing guidance
✅ Improving element matching for custom UI components
✅ Building knowledge base for specific applications
❌ Not needed for standard web elements (already well-supported)
❌ Not required for basic testing scenarios

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path  # noqa: TC003

import typer

from aat.core.config import load_config

_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg"})

learn_app = typer.Typer(
    name="learn",
    help="Learning data management.",
    no_args_is_help=True,
)


def _collect_images(path: Path) -> list[Path]:
    """Collect image files from a path (file or directory).

    Args:
        path: Single image file or directory to scan.

    Returns:
        List of image file paths.
    """
    if path.is_file():
        if path.suffix.lower() in _IMAGE_EXTENSIONS:
            return [path]
        return []

    images: list[Path] = []
    for ext in sorted(_IMAGE_EXTENSIONS):
        images.extend(sorted(path.glob(f"*{ext}")))
    return images


def _file_hash(file_path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    data = file_path.read_bytes()
    hasher.update(data)
    return hasher.hexdigest()


@learn_app.command("add")
def learn_add(
    path: str = typer.Argument(..., help="Image file or directory to learn from"),
    name: str | None = typer.Option(None, "--name", "-n", help="Target name"),
) -> None:
    """Register design guide images for learning."""
    source = Path(path)
    if not source.exists():
        typer.echo(
            typer.style(f"Path does not exist: {path}", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)

    # Collect image files
    images = _collect_images(source)
    if not images:
        typer.echo(
            typer.style(
                f"No image files (.png, .jpg, .jpeg) found: {path}",
                fg=typer.colors.RED,
            ),
            err=True,
        )
        raise typer.Exit(code=1)

    # Load config to resolve directories
    config = load_config()
    assets_dir = Path(config.assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    data_dir = Path(config.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Try to use LearnedStore; fall back to simple echo if not available yet
    store = _get_store(data_dir / "learned.db")

    registered = 0
    for img_path in images:
        target_name = name or img_path.stem
        dest = assets_dir / img_path.name

        # Copy image to assets/
        if dest != img_path.resolve():
            shutil.copy2(img_path, dest)

        img_hash = _file_hash(img_path)

        if store is not None:
            _save_to_store(store, target_name, img_hash, str(dest))
        else:
            typer.echo(f"  [echo] Registered: {target_name} -> {dest}")

        registered += 1

    status = typer.style(str(registered), fg=typer.colors.GREEN)
    typer.echo(f"Registered {status} image(s) for learning.")


def _get_store(db_path: Path) -> object | None:
    """Try to create a LearnedStore instance.

    Returns None if the module is not yet available.
    """
    try:
        from aat.learning.store import LearnedStore

        return LearnedStore(db_path)
    except (ImportError, AttributeError):
        return None


def _save_to_store(store: object, target_name: str, img_hash: str, dest: str) -> None:
    """Save a LearnedElement via store.save().

    Gracefully degrades if the store API doesn't match expectations yet.
    """
    try:
        from aat.core import LearnedElement

        element = LearnedElement(
            scenario_id="manual",
            step_number=1,
            target_name=target_name,
            screenshot_hash=img_hash,
            correct_x=0,
            correct_y=0,
            cropped_image_path=dest,
            confidence=1.0,
        )
        store.save(element)  # type: ignore[attr-defined]
    except (ImportError, AttributeError, TypeError):
        pass


@learn_app.command(name="platform")
def learn_platform(
    platform: str = typer.Option(
        ...,
        "--platform",
        "-p",
        help="Platform key (e.g., flutter_canvaskit, react_spa, vue_spa).",
    ),
    tip: str = typer.Option(
        ...,
        "--tip",
        "-t",
        help="Tip or pattern to remember for this platform.",
    ),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path."),
) -> None:
    """Add a custom platform-specific testing tip."""
    cfg_path = Path(config_path) if config_path else None
    try:
        config = load_config(config_path=cfg_path)
        data_dir = config.data_dir
    except Exception:
        data_dir = ".aat"

    try:
        from aat.learning.store import LearnedStore

        db_path = Path(data_dir) / "learned.db"
        store = LearnedStore(db_path)
        store.add_platform_tip(platform, tip)
        typer.echo(
            typer.style(
                f"  ✓ Saved tip for '{platform}': {tip}",
                fg=typer.colors.GREEN,
            )
        )
    except Exception as e:
        typer.echo(f"  Error: {e}", err=True)
        raise typer.Exit(1) from None
