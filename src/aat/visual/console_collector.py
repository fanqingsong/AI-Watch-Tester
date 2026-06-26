"""
════════════════════════════════════════════════════════════════════════════════
                    🐛 Browser Console Error Collector
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Captures and aggregates browser console errors, warnings, and page errors
during test execution. Attaches to Playwright page event handlers to collect
JavaScript issues in real-time, providing diagnostic context for test failures
and frontend quality monitoring.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Attach collector to Playwright page before test execution
collector = ConsoleCollector()
collector.attach(page)

# Run test steps (errors collected automatically)
await page.click("#submit-button")
await page.wait_for_url("*/success")

# Check for errors after execution
if collector.error_count > 0:
    print(f"Test completed with {collector.error_count} console errors:")
    for error in collector.errors:
        print(f"  → {error.text} at {error.url}:{error.line_number}")

# Clear for next scenario
collector.reset()
```

⚙️  CORE ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
    ConsoleCollector
         ├── attach()           → Register listeners on Playwright page
         ├── _on_console()      → Handle console message events
         ├── _on_pageerror()    → Handle uncaught exception events
         ├── errors             → Filter only error-level entries
         ├── warnings           → Filter only warning-level entries
         ├── error_count        → Quick access to error total
         ├── reset()            → Clear entries for next scenario
         ├── format_summary()   → One-line status string
         └── format_details()   → Multi-line error listing

    Event Attachment:
    ┌─────────────────────────────────────────────────────────────────┐
    │ page.on("console", collector._on_console)                       │
    │   ↓ Captures: console.log(), console.error(), console.warn()    │
    │                                                                 │
    │ page.on("pageerror", collector._on_pageerror)                   │
    │   ↓ Captures: Uncaught exceptions, rejected promises            │
    └─────────────────────────────────────────────────────────────────┘

    Data Flow:
    ┌─────────────────────────────────────────────────────────────────┐
    │ Browser Event                                                   │
    │    ↓                                                            │
    │ Callback Handler (_on_console or _on_pageerror)                 │
    │    ↓                                                            │
    │ Extract: level, text, url, line_number                         │
    │    ↓                                                            │
    │ Store ConsoleEntry in entries list                             │
    │    ↓                                                            │
    │ Query via errors/warnings/error_count properties               │
    └─────────────────────────────────────────────────────────────────┘

    Entry Structure:
    ConsoleEntry:
      ├── level: "error" | "warning" | "info" | "log"
      ├── text: Error message or log content
      ├── url: Source file URL (if available)
      └── line_number: Line number in source file

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- Real-Time Collection: Attaches to browser events for immediate capture
- Event Filtering: Automatically filters errors and warnings from noise
- Source Tracking: Captures URL and line numbers for debugging
- Dual Event Types: Handles both console API calls and uncaught errors
- Filtered Views: Separate accessors for errors and warnings
- Reset Capability: Clear state between test scenarios
- Formatted Output: Ready-to-use summary and detail strings for reports
- Idempotent Attachment: Safe to call attach() multiple times

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- No duplicate detection (same error logged multiple times)
- No grouping by error type (each entry is separate)
- URL extraction may fail for some browser errors (empty string fallback)
- Line numbers not always available (0 when unknown)
- No buffering/limit (memory grows with error count in long sessions)
- Only captures errors from attached page (not iframes or web workers)

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Always attach collectors before running test steps
- Reset collectors between scenarios to avoid cross-contamination
- Use error_count for quick pass/fail gates in assertions
- Archive format_details() output when investigating failures
- Pair with screenshot capture for full context on errors
- Consider implementing grouping for duplicate error suppression

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ E2E test execution with frontend quality validation
✅ Regression testing with console error monitoring
✅ Pre-production deployment smoke tests
✅ Detecting JavaScript errors not visible in UI
❌ Don't use for backend error monitoring (server logs instead)

════════════════════════════════════════════════════════════════════════════════
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
