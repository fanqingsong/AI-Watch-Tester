"""
════════════════════════════════════════════════════════════════════════════════
                       🏗️  Base Engine Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines BaseEngine abstract interface that all test engines must implement.
WebEngine (Playwright) and DesktopEngine (PyAutoGUI) inherit from this ABC.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.engine.web import WebEngine
from aat.engine.desktop import DesktopEngine
from aat.core import EngineConfig

# Web engine (Playwright)
web_engine = WebEngine(EngineConfig(type="web", browser="chromium"))
await web_engine.start()
await web_engine.navigate("https://example.com")
screenshot = await web_engine.screenshot()
await web_engine.stop()

# Desktop engine (PyAutoGUI)
desktop_engine = DesktopEngine(EngineConfig(type="desktop"))
await desktop_engine.start()
await desktop_engine.click_at(100, 200)
await desktop_engine.stop()
```

⚙️  ENGINE INTERFACE
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  BaseEngine (Abstract Interface)                                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Lifecycle:                                                                 │
│  • start()              → Initialize engine (launch browser/app)           │
│  • stop()               → Cleanup and close resources                       │
│                                                                             │
│  Navigation:                                                                 │
│  • navigate(url)       → Navigate to URL (web only)                       │
│  • go_back()            → Go back in history (web only)                     │
│  • refresh()            → Reload current page (web only)                    │
│                                                                             │
│  Mouse:                                                                      │
│  • click(x, y)         → Click at coordinates                              │
│  • double_click(x, y)   → Double-click at coordinates                      │
│  • right_click(x, y)    → Right-click at coordinates                       │
│                                                                             │
│  Keyboard:                                                                   │
│  • type_text(text)      → Type text string                                  │
│  • press_key(key)       → Press single key                                  │
│  • key_combo(keys)      → Press key combination                             │
│                                                                             │
│  Utilities:                                                                 │
│  • screenshot()         → Capture screenshot bytes                           │
│  • get_url()            → Get current URL (web only)                       │
│  • get_page_text()      → Get page source/text                             │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

🔧 ENGINE IMPLEMENTATIONS
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  WebEngine (Playwright)                  │  DesktopEngine (PyAutoGUI)       │
├────────────────────────────────────────────────────────────────────────────┤
│  • Async API                             │  • Sync operations (run in executor) │
│  • Multi-browser support                 │  • OS-level UI automation         │
│  • Fast, reliable                        │  • Works with any desktop app      │
│  • Headless mode support                 │  • Coordinate-based interaction    │
│  • Network interception                  │  • Limited reliability              │
└────────────────────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path  # noqa: TC003


class BaseEngine(ABC):
    """Test engine abstract interface."""

    @abstractmethod
    async def start(self) -> None:
        """Initialize engine (launch browser etc.)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Shut down engine (close browser etc.)."""
        ...

    @abstractmethod
    async def screenshot(self) -> bytes:
        """Capture current screen as PNG bytes."""
        ...

    @abstractmethod
    async def click(self, x: int, y: int) -> None:
        """Click at coordinates."""
        ...

    @abstractmethod
    async def double_click(self, x: int, y: int) -> None:
        """Double-click at coordinates."""
        ...

    @abstractmethod
    async def right_click(self, x: int, y: int) -> None:
        """Right-click at coordinates."""
        ...

    @abstractmethod
    async def type_text(self, text: str) -> None:
        """Type text at current focus."""
        ...

    @abstractmethod
    async def press_key(self, key: str) -> None:
        """Press a single key (Enter, Tab, Escape etc.)."""
        ...

    @abstractmethod
    async def key_combo(self, *keys: str) -> None:
        """Press key combination (Ctrl+A, Cmd+C etc.)."""
        ...

    @abstractmethod
    async def navigate(self, url: str) -> None:
        """Navigate to URL."""
        ...

    @abstractmethod
    async def go_back(self) -> None:
        """Go back."""
        ...

    @abstractmethod
    async def refresh(self) -> None:
        """Refresh page."""
        ...

    @abstractmethod
    async def scroll(self, x: int, y: int, delta: int) -> None:
        """Scroll at coordinates. delta > 0: down, delta < 0: up."""
        ...

    @abstractmethod
    async def move_mouse(self, x: int, y: int) -> None:
        """Move mouse pointer (no click)."""
        ...

    @abstractmethod
    async def get_url(self) -> str:
        """Return current URL."""
        ...

    @abstractmethod
    async def get_page_text(self) -> str:
        """Return visible text of current page."""
        ...

    @abstractmethod
    async def save_screenshot(self, path: Path) -> Path:
        """Save screenshot to file and return path."""
        ...

    @abstractmethod
    async def find_text_position(self, text: str) -> tuple[int, int] | None:
        """Find screen position of visible text. Returns (x, y) or None."""
        ...
