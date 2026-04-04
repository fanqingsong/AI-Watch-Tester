"""Console error collector — captures browser JS errors during test execution.

Attaches to Playwright page events (console, pageerror) and collects
errors/warnings for reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConsoleEntry:
    """A single console message or page error."""

    level: str  # "error", "warning", "info", etc.
    text: str
    url: str = ""
    line_number: int = 0


@dataclass
class ConsoleCollector:
    """Collects browser console errors from a Playwright page.

    Usage::

        collector = ConsoleCollector()
        collector.attach(page)  # start collecting
        # ... run steps ...
        errors = collector.errors  # get collected errors
        collector.reset()  # clear for next scenario
    """

    entries: list[ConsoleEntry] = field(default_factory=list)
    _attached: bool = field(default=False, repr=False)

    def attach(self, page: object) -> None:
        """Attach console/pageerror listeners to a Playwright page."""
        if self._attached:
            return

        # page.on("console", ...) — all console messages
        page.on("console", self._on_console)  # type: ignore[attr-defined]
        # page.on("pageerror", ...) — uncaught exceptions
        page.on("pageerror", self._on_pageerror)  # type: ignore[attr-defined]
        self._attached = True

    def _on_console(self, msg: object) -> None:
        """Handle console message event."""
        msg_type = getattr(msg, "type", "log")
        if msg_type in ("error", "warning"):
            text = getattr(msg, "text", str(msg))
            location = getattr(msg, "location", None)
            url = ""
            line = 0
            if location:
                url = getattr(location, "url", "") or location.get("url", "")  # type: ignore[union-attr]
                line = getattr(location, "lineNumber", 0) or location.get("lineNumber", 0)  # type: ignore[union-attr]
            self.entries.append(ConsoleEntry(level=msg_type, text=text, url=url, line_number=line))

    def _on_pageerror(self, error: object) -> None:
        """Handle uncaught page error event."""
        text = str(error)
        self.entries.append(ConsoleEntry(level="error", text=text))

    @property
    def errors(self) -> list[ConsoleEntry]:
        """Return only error-level entries."""
        return [e for e in self.entries if e.level == "error"]

    @property
    def warnings(self) -> list[ConsoleEntry]:
        """Return only warning-level entries."""
        return [e for e in self.entries if e.level == "warning"]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def reset(self) -> None:
        """Clear collected entries for next scenario."""
        self.entries.clear()

    def format_summary(self, step_num: int) -> str:
        """Format a one-line summary for a step."""
        errs = self.error_count
        if errs == 0:
            return f"step{step_num:03d}  (console: 0 errors)"
        return f"step{step_num:03d}  (console: {errs} errors)"

    def format_details(self) -> list[str]:
        """Format detailed error lines for display."""
        lines: list[str] = []
        for e in self.errors:
            loc = ""
            if e.url:
                loc = f" (line {e.line_number})" if e.line_number else ""
                loc = f"{e.url}{loc}"
            if loc:
                lines.append(f"  → {e.text} {loc}")
            else:
                lines.append(f"  → {e.text}")
        return lines
