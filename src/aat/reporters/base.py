"""
════════════════════════════════════════════════════════════════════════════════
                    📊 Test Report Generator Interface
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines the abstract base class for all test report generators in AAT.
Provides a consistent interface for converting TestResult and LoopResult
objects into human-readable or machine-readable output formats.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Generate a Markdown report after test execution
reporter = MarkdownReporter()
report_path = await reporter.generate(
    result=test_result,
    output_dir=Path("reports/run_001")
)

# Generate an HTML report for CI/CD display
html_reporter = HTMLReporter()
html_path = await html_reporter.generate(
    result=loop_result,
    output_dir=Path("reports/latest")
)
```

⚙️  CORE ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
    BaseReporter (ABC)
         ├── generate()         → Convert TestResult/LoopResult to report file
         └── format_name       → Identifier for report format

    Implementation Pattern:
    MarkdownReporter ────────────┐
    HTMLReporter ─────────────────┤── All implement BaseReporter interface
    JSONReporter ─────────────────┤
    JUnitReporter ────────────────┘

    Report Generation Flow:
    ┌─────────────────────────────────────────────────────────────────┐
    │ Input: TestResult or LoopResult                                 │
    │                         ↓                                        │
    │ 1. Validate output directory exists (create if needed)          │
    │                         ↓                                        │
    │ 2. Format-specific rendering (Markdown/HTML/JSON/etc)           │
    │                         ↓                                        │
    │ 3. Write report file(s) to output_dir                           │
    │                         ↓                                        │
    │ 4. Return path to primary report file                           │
    └─────────────────────────────────────────────────────────────────┘

    Result Type Handling:
    TestResult → Single test run, step-by-step details
    LoopResult → DevQA loop with multiple iterations + AI fixes

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- Abstract Generate Method: Defines signature for report generation
- Format Identification: Each reporter declares its format via format_name
- Output Management: Handles directory creation and file path resolution
- Type Safety: Uses Path objects for filesystem operations
- Dual Result Support: Handles both single runs (TestResult) and loops (LoopResult)

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- All generate() methods are async - must use await when calling
- Reporters should handle both TestResult and LoopResult types
- Output directory creation is reporter's responsibility
- Failure during file writing should raise ReporterError
- Reporters should not modify the original result object

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Include both human-readable (Markdown/HTML) and machine-readable (JSON) output
- Organize reports in timestamped directories for historical tracking
- Provide meaningful file names (e.g., report.md, summary.json)
- Handle large result sets efficiently (pagination, summaries)
- Include visual elements where appropriate (tables, charts, status badges)

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ After test execution to document results
✅ In CI/CD pipelines for result archiving and display
✅ For generating test summaries and regression reports
❌ Don't use for real-time progress streaming (use callbacks instead)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aat.core import LoopResult, TestResult


class BaseReporter(ABC):
    """Report generation abstract interface."""

    @abstractmethod
    async def generate(
        self,
        result: TestResult | LoopResult,
        output_dir: Path,
    ) -> Path:
        """Generate report file from test results.

        Args:
            result: TestResult (single run) or LoopResult (loop run).
            output_dir: Output directory for the report.

        Returns:
            Path to the generated report file.
        """
        ...

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Report format name: 'markdown', 'html'."""
        ...
