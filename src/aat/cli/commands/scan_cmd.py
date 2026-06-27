# ruff: noqa: E501  # embeds long inline JavaScript passed to page.evaluate
"""
════════════════════════════════════════════════════════════════════════════════
                   🔍 Page Scanning & Element Detection Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Scans web pages to collect interactive UI elements for scenario generation and
element matching. Uses multi-source detection (accessibility, DOM, Flutter Semantics,
OCR) to build comprehensive element maps with coordinates, selectors, and labels.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Basic page scan
aat scan --url http://localhost:3000/login

# Compare with previous scan
aat scan --url http://localhost:3000 --compare .aat/scan_result.json

# Scan post-login page with session
aat scan --url http://localhost:3000/dashboard --session user_session

# Use with custom config
aat scan --url http://localhost:3000 --config aat.config.yaml
```

⚙️  MULTI-SOURCE ELEMENT DETECTION
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│                     Page Element Collection                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Accessibility Tree (Primary - High Quality)               │  │
│  │    - ARIA roles and labels                                     │  │
│  │    - Semantic element types                                    │  │
│  │    - Filters decorative elements                               │  │
│  │    - Provides stable ref identifiers (e5, e10, etc.)          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 2. DOM Elements (Fallback)                                   │  │
│  │    - CSS selectors                                            │  │
│  │    - Element coordinates                                      │  │
│  │    - Text content extraction                                 │  │
│  │    - SVG button detection                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 3. Flutter Semantics (CanvasKit Apps)                        │  │
│  │    - Shadow DOM navigation                                    │  │
│  │    - Aria-label extraction                                    │  │
│  │    - Semantics node detection                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 4. OCR (Last Resort)                                          │  │
│  │    - Text recognition with coordinates                        │  │
│  │    - Multi-language support (English + Korean)                │  │
│  │    - Confidence-based filtering                               │  │
│  │    - Duplicate detection                                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **multi-source collection**: Combines accessibility, DOM, Semantics, and OCR
- **Flutter detection**: Automatic CanvasKit detection and Semantics activation
- **element deduplication**: Removes overlapping elements from multiple sources
- **coordinate mapping**: Provides x,y coordinates for all elements
- **comparison mode**: Detects added, removed, and moved elements
- **session support**: Can load saved sessions for authenticated page scanning

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- OCR requires Tesseract installation and language data
- Flutter Semantics requires page stabilization delay
- Shadow DOM navigation may not work with all Flutter versions
- OCR text accuracy depends on image quality and font clarity
- Element count limited to 120 for token efficiency

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Scan pages after major UI changes to update element references
- Use comparison mode to detect UI regressions
- For authenticated pages, save session and use --session flag
- Review scan results to verify element detection quality
- Use scan results with aat generate --scan for accurate scenario generation

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Before generating test scenarios (aat generate --scan)
✅ After UI changes to update element references
✅ When tests fail due to element detection issues
✅ For debugging element matching problems
❌ Not needed for simple page navigation tests
❌ Not required if using stable CSS selectors

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import typer

from aat.core.config import load_config
from aat.core.exceptions import AATError


def scan_command(
    url: str = typer.Option(..., "--url", "-u", help="URL to scan."),
    compare: str | None = typer.Option(
        None,
        "--compare",
        help="Previous scan_result.json to diff against.",
    ),
    session: str | None = typer.Option(
        None,
        "--session",
        help="Load saved session before scanning (for post-login pages).",
    ),
    config_path: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Scan a URL and collect UI elements (selectors, OCR text, coordinates)."""
    try:
        asyncio.run(_scan(url, compare, session, config_path))
    except AATError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None


async def _scan(
    url: str,
    compare_path: str | None,
    session_name: str | None,
    config_path: str | None,
) -> None:
    """Execute scan asynchronously."""
    from aat.core import EngineConfig
    from aat.engine.web import WebEngine

    cfg_path = Path(config_path) if config_path else None
    config = load_config(config_path=cfg_path)

    engine_config = EngineConfig(
        type="web",
        headless=True,
        viewport_width=config.engine.viewport_width,
        viewport_height=config.engine.viewport_height,
    )
    engine = WebEngine(engine_config)

    typer.echo(f"[AWT] Scanning {url}...")
    start = time.monotonic()

    try:
        await engine.start()

        # Load session if provided (for scanning post-login pages)
        if session_name:
            session_path = Path(config.data_dir) / "sessions" / f"{session_name}.json"
            if session_path.exists():
                typer.echo(f"[AWT] Loading session: {session_name}")
                await engine.load_session(str(session_path))
            else:
                typer.echo(f"[AWT] Session '{session_name}' not found, scanning without login")

        await engine.navigate(url)

        # Wait for page to settle (longer for Flutter CanvasKit + dynamic content)
        await asyncio.sleep(5.0)

        page = engine.page

        # 1. Screenshot
        scan_dir = Path(config.data_dir) / "scans"
        scan_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        ss_path = scan_dir / f"scan_{ts}.png"
        ss_bytes = await engine.screenshot()
        ss_path.write_bytes(ss_bytes)

        # 2. Detect Flutter
        from aat.engine.flutter_semantics import (
            activate_semantics,
            get_all_semantics_labels,
            is_flutter_page,
        )

        is_flutter = await is_flutter_page(page)
        if is_flutter:
            typer.echo("[AWT] Flutter CanvasKit detected — activating Semantics...")
            await activate_semantics(page)

            # Wait for stable Semantics node count (max 10s)
            from aat.engine.flutter_semantics import _count_semantics_nodes

            prev_count = -1
            stable_rounds = 0
            for _ in range(10):
                await asyncio.sleep(1.0)
                count = await _count_semantics_nodes(page)
                if count == prev_count and count > 0:
                    stable_rounds += 1
                    if stable_rounds >= 2:
                        break
                else:
                    stable_rounds = 0
                prev_count = count
            typer.echo(f"[AWT] Semantics stable: {prev_count} nodes")

        # 3. Collect elements
        elements: list[dict[str, Any]] = []

        # 3a. Accessibility tree (primary source - semantic, filters decorative elements)
        typer.echo("[AWT] Collecting accessibility elements...")
        a11y_elements = await _collect_accessibility_elements(page)
        elements.extend(a11y_elements)

        # 3b. DOM fallback (only if accessibility returns no results)
        if not a11y_elements:
            typer.echo("[AWT] No accessibility elements, using DOM fallback")
            # Setup console listener to capture debug messages
            console_messages = []

            def on_console(msg):
                if msg.type == "log":
                    console_messages.append(msg.text)
                    typer.echo(f"  [Browser Console] {msg.text}")

            page.on("console", on_console)

            dom_elements = await _collect_dom_elements(page)
            elements.extend(dom_elements)

            # Remove console listener
            page.remove_listener("console", on_console)

        # 3c. Flutter Semantics elements
        if is_flutter:
            sem_elements = await _collect_semantics_elements(page)
            elements.extend(sem_elements)
            sem_labels = await get_all_semantics_labels(page)
            typer.echo(f"[AWT] Semantics labels: {len(sem_labels)}")

        # 3d. OCR elements
        ocr_elements = await _collect_ocr_elements(ss_bytes)
        # Deduplicate: skip OCR results that overlap with DOM/Semantics
        for ocr_el in ocr_elements:
            if not _is_duplicate(ocr_el, elements):
                elements.append(ocr_el)

        # 4. Build result
        elapsed = (time.monotonic() - start) * 1000
        result = {
            "url": url,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "screenshot": str(ss_path),
            "is_flutter": is_flutter,
            "viewport": {
                "width": engine_config.viewport_width,
                "height": engine_config.viewport_height,
            },
            "elements": elements,
            "element_count": len(elements),
            "elapsed_ms": round(elapsed, 0),
        }

        # 5. Save
        out_path = Path(config.data_dir) / "scan_result.json"
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        typer.echo(f"[AWT] Found {len(elements)} elements in {elapsed:.0f}ms")
        typer.echo(f"[AWT] Screenshot: {ss_path}")
        typer.echo(f"[AWT] Result: {out_path}")

        # 6. Compare if requested
        if compare_path:
            _compare_scans(out_path, Path(compare_path))

    finally:
        await engine.stop()


# -- Element collectors -------------------------------------------------------


async def _collect_dom_elements(page: Any) -> list[dict[str, Any]]:
    """Collect clickable/interactive DOM elements with bounding boxes."""
    try:
        elements: list[dict[str, Any]] = await page.evaluate("""() => {
            const results = [];
            const selectors = [
                'a', 'button', 'input', 'textarea', 'select', 'label',
                '[role="button"]', '[role="link"]', '[role="tab"]',
                '[role="menuitem"]', '[role="checkbox"]', '[role="switch"]',
                '[onclick]', '[tabindex]',
                '[type="button"]', '[type="submit"]', '[type="image"]',
                'svg',  // SVG icon buttons
            ];
            const seen = new Set();

            for (const sel of selectors) {
                for (const el of document.querySelectorAll(sel)) {
                    if (seen.has(el)) continue;
                    seen.add(el);

                    const rect = el.getBoundingClientRect();
                    if (rect.width < 4 || rect.height < 4) continue;
                    if (rect.x < 0 || rect.y < 0) continue;

                    let label = (
                        el.textContent?.trim()?.substring(0, 80) ||
                        el.getAttribute('aria-label') ||
                        el.getAttribute('placeholder') ||
                        el.getAttribute('title') ||
                        ''
                    );
                    // For elements without visible text, generate a descriptive label
                    if (!label || label.length < 1) {
                        const tagName = el.tagName.toLowerCase();
                        const type = el.getAttribute('type') || '';
                        const role = el.getAttribute('role') || '';
                        if (type === 'submit' || role === 'button' || tagName === 'button') {
                            label = 'submit_button';
                        } else if (type === 'image') {
                            label = 'image_button';
                        } else if (tagName === 'svg') {
                            // SVG icons are usually inside <button> or <a>
                            // Try to get aria-label from button parent
                            const buttonParent = el.closest('button, a, [role="button"]');
                            if (buttonParent) {
                                // Get parent's attributes first
                                const parentLabel = buttonParent.getAttribute('aria-label');
                                const parentTitle = buttonParent.getAttribute('title');
                                const parentId = buttonParent.getAttribute('id');
                                const parentClass = buttonParent.className;
                                const parentText = buttonParent.textContent?.trim()?.substring(0, 40);

                                // Debug: log to console (won't appear in output but helpful for debugging)
                                console.log('[SVG Debug] Found button parent:', {
                                    parentLabel, parentTitle, parentId, parentClass, parentText
                                });

                                label = parentLabel || parentTitle || parentText || parentId || parentClass || 'svg_button';
                            } else {
                                // No button parent - check direct parent
                                const directParent = el.parentElement;
                                const parentTag = directParent?.tagName.toLowerCase();
                                const parentId = directParent?.getAttribute('id');
                                const parentClass = directParent?.className;
                                const parentText = directParent?.textContent?.trim()?.substring(0, 40);

                                console.log('[SVG Debug] No button parent, checking direct parent:', {
                                    parentTag, parentId, parentClass, parentText
                                });

                                // Use explicit checks to avoid empty string blocking fallback
                                label = 'svg_icon';  // default
                                if (parentText && parentText.length > 0) {
                                    label = parentText;
                                } else if (parentId && parentId.length > 0) {
                                    label = parentId;
                                } else if (parentClass && parentClass.length > 0) {
                                    label = parentClass;
                                }
                            }
                        } else if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
                            label = 'input_field';
                        } else {
                            label = `${tagName}_${role || type || 'element'}`;
                        }
                    }
                    // Still skip if label is too short (probably noise)
                    if (label.length < 2) continue;

                    let selector = _bestSelector(el);
                    // For SVG inside button/a, use the button's selector for more reliable clicking
                    if (el.tagName.toLowerCase() === 'svg') {
                        const buttonParent = el.closest('button, a, [role="button"]');
                        if (buttonParent) {
                            selector = _bestSelector(buttonParent);
                        }
                    }

                    results.push({
                        label: label,
                        type: el.tagName.toLowerCase(),
                        input_type: el.getAttribute('type') || '',
                        role: el.getAttribute('role') || '',
                        selector: selector,
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        source: 'dom',
                    });
                }
            }

            function _bestSelector(el) {
                if (el.id) return '#' + el.id;
                if (el.className && typeof el.className === 'string') {
                    const cls = el.className.trim().split(/\\s+/)[0];
                    if (cls) return el.tagName.toLowerCase() + '.' + cls;
                }
                return el.tagName.toLowerCase();
            }

            return results;
        }""")
        return elements  # type: ignore[return-value]
    except Exception:
        return []


async def _collect_accessibility_elements(
    page: Any,
    interesting_only: bool = True,
) -> list[dict[str, Any]]:
    """Collect elements using Playwright accessibility snapshot.

    Advantages over DOM collection:
    - Automatically filters decorative elements (footer, logo, icon-only)
    - Provides semantic roles (button, textbox, link)
    - Unique ref identifiers (e5, e10, e20) stable within snapshot
    - User-centric labels (e.g., "textbox 'What needs...'" not just "<input>")

    Args:
        page: Playwright Page object
        interesting_only: Only include interactive elements (default True)

    Returns:
        List of elements with snapshot_ref and semantic information
    """
    try:
        import logging
        import re

        logger = logging.getLogger(__name__)

        # Call Playwright aria_snapshot (Playwright 1.60+ API)
        # mode="ai" gives us ref=e5 style references
        # boxes=True gives us bounding box coordinates
        snapshot_str = await page.aria_snapshot(mode="ai", boxes=True)

        elements: list[dict[str, Any]] = []

        # Parse the aria snapshot string format:
        # - role "name" [attributes] [ref=e5] [box=x,y,w,h]
        # Examples:
        # - searchbox "输入搜索词" [active] [ref=e6] [box=356,149,549,42]
        # - button "Submit" [box=942,170,0,0]
        lines = snapshot_str.strip().split("\n")

        for line in lines:
            # Parse role, name, ref, and box from each line
            # Pattern: - role "name" [attributes] [ref=e#] [box=x,y,w,h]
            # or: - role [attributes] [ref=e#] [box=x,y,w,h]

            # Skip empty lines or non-element lines
            if not line.strip().startswith("-"):
                continue

            # Extract role (first word after dash, accounting for leading spaces)
            role_match = re.search(r"-\s+(\S+)", line)
            if not role_match:
                continue
            role = role_match.group(1)

            # Extract accessible name (quoted string if present)
            name_match = re.search(r'"([^"]*)"', line)
            name = name_match.group(1) if name_match else ""

            # Extract ref (e.g., ref=e6)
            ref_match = re.search(r"\[ref=(e\d+)\]", line)
            ref = ref_match.group(1) if ref_match else None

            # Extract box coordinates (e.g., box=356,149,549,42)
            box_match = re.search(r"\[box=(\d+),(\d+),(\d+),(\d+)\]", line)
            if not box_match:
                continue  # Skip elements without bounding box

            x, y, width, height = map(int, box_match.groups())

            # Skip elements with invalid coordinates
            if x < 0 or y < 0:
                continue

            # Skip tiny elements (<4px) UNLESS they're buttons/links with valid coordinates
            # Buttons/links with 0x0 size but valid coordinates might be hidden submit buttons
            # or elements with incomplete accessibility tree data
            if (width < 4 or height < 4) and role not in ("button", "link", "submit"):
                continue

            # Filter footer elements (bottom 15% of viewport)
            viewport_height = 720  # TODO: Get from config
            if y > viewport_height * 0.85:
                continue

            # Skip generic containers without refs (probably layout elements)
            if role == "generic" and not ref:
                continue

            # Build element record
            element = {
                "label": name or role or f"{role}_element",
                "type": "accessibility",
                "role": role,
                "snapshot_ref": ref,
                "accessible_name": name,
                "selector": f"[ref={ref}]" if ref else f"[role={role}]",
                "x": round(x + width / 2),
                "y": round(y + height / 2),
                "width": round(width),
                "height": round(height),
                "source": "accessibility",
            }

            elements.append(element)

        typer.echo(f"[Accessibility] Collected {len(elements)} elements")
        logger.info("[Accessibility] Collected %d elements", len(elements))
        return elements

    except Exception as e:
        typer.echo(f"[Accessibility] Exception occurred: {type(e).__name__}: {e}")
        logger.warning("Accessibility snapshot failed: %s", e)
        return []


async def _collect_semantics_elements(page: Any) -> list[dict[str, Any]]:
    """Collect Flutter Semantics elements with bounding boxes (shadow DOM aware)."""
    try:
        elements: list[dict[str, Any]] = await page.evaluate("""() => {
            const results = [];

            // Collect from all possible locations (direct + shadow DOM)
            let nodes = document.querySelectorAll('flt-semantics');

            // Flutter 3.x: flutter-view shadow DOM
            if (nodes.length === 0) {
                const fv = document.querySelector('flutter-view');
                if (fv && fv.shadowRoot) {
                    nodes = fv.shadowRoot.querySelectorAll('flt-semantics');
                }
            }

            // Flutter 2.x: flt-glass-pane shadow DOM
            if (nodes.length === 0) {
                const gp = document.querySelector('flt-glass-pane');
                if (gp && gp.shadowRoot) {
                    nodes = gp.shadowRoot.querySelectorAll('flt-semantics');
                }
            }

            for (const node of nodes) {
                const label = node.getAttribute('aria-label');
                if (!label) continue;

                const rect = node.getBoundingClientRect();
                if (rect.width < 2 || rect.height < 2) continue;

                results.push({
                    label: label,
                    type: node.getAttribute('role') || 'semantics',
                    role: node.getAttribute('role') || '',
                    selector: 'flt-semantics[aria-label="'
                        + label.replace(/"/g, '\\\\"') + '"]',
                    x: Math.round(rect.x + rect.width / 2),
                    y: Math.round(rect.y + rect.height / 2),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    source: 'semantics',
                });
            }
            return results;
        }""")
        return elements  # type: ignore[return-value]
    except Exception:
        return []


async def _collect_ocr_elements(
    screenshot: bytes,
) -> list[dict[str, Any]]:
    """Collect text elements via OCR."""
    try:
        import cv2
        import numpy as np
        import pytesseract  # type: ignore[import-untyped]

        arr = np.frombuffer(screenshot, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return []

        # Preprocess
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        img = clahe.apply(img)
        h, w = img.shape
        img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        data = pytesseract.image_to_data(
            img,
            lang="eng+kor",
            config="--oem 3",
            output_type=pytesseract.Output.DICT,
        )

        elements: list[dict[str, Any]] = []
        n = len(data.get("text", []))
        for i in range(n):
            conf = data["conf"][i]
            if not isinstance(conf, (int, float)) or conf <= 30:
                continue
            text = str(data["text"][i]).strip()
            if len(text) < 2:
                continue

            # 2x upscale → original coords
            left = int(data["left"][i]) // 2
            top = int(data["top"][i]) // 2
            wd = int(data["width"][i]) // 2
            ht = int(data["height"][i]) // 2

            elements.append(
                {
                    "label": text,
                    "type": "text",
                    "role": "",
                    "selector": "",
                    "x": left + wd // 2,
                    "y": top + ht // 2,
                    "width": wd,
                    "height": ht,
                    "source": "ocr",
                    "confidence": round(float(conf) / 100, 2),
                }
            )

        return elements
    except Exception:
        return []


def _is_duplicate(
    ocr_el: dict[str, Any],
    existing: list[dict[str, Any]],
    distance: int = 30,
) -> bool:
    """Check if OCR element overlaps with an existing element."""
    ox, oy = ocr_el["x"], ocr_el["y"]
    return any(abs(el["x"] - ox) < distance and abs(el["y"] - oy) < distance for el in existing)


# -- Compare scans -----------------------------------------------------------


def _compare_scans(current_path: Path, previous_path: Path) -> None:
    """Compare two scan results and output differences."""
    try:
        current = json.loads(current_path.read_text("utf-8"))
        previous = json.loads(previous_path.read_text("utf-8"))
    except Exception as e:
        typer.echo(f"[AWT] Compare failed: {e}")
        return

    prev_map = {el["label"]: el for el in previous.get("elements", [])}
    curr_map = {el["label"]: el for el in current.get("elements", [])}

    added = [k for k in curr_map if k not in prev_map]
    removed = [k for k in prev_map if k not in curr_map]
    moved = []
    for label in curr_map:
        if label in prev_map:
            c, p = curr_map[label], prev_map[label]
            if abs(c["x"] - p["x"]) > 10 or abs(c["y"] - p["y"]) > 10:
                moved.append((label, p, c))

    if not added and not removed and not moved:
        typer.echo("[AWT] No changes detected.")
        return

    typer.echo("")
    typer.echo("=== AWT SCAN DIFF ===")
    for label in added:
        el = curr_map[label]
        typer.echo(f'  + NEW: "{label}" at ({el["x"]}, {el["y"]})')
    for label in removed:
        el = prev_map[label]
        typer.echo(f'  - REMOVED: "{label}" was at ({el["x"]}, {el["y"]})')
    for label, prev, curr in moved:
        typer.echo(f'  ~ MOVED: "{label}" ({prev["x"]},{prev["y"]}) → ({curr["x"]},{curr["y"]})')
    typer.echo(f"  Total: +{len(added)} -{len(removed)} ~{len(moved)}")
    typer.echo("=====================")
    typer.echo("")
