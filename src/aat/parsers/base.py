"""
════════════════════════════════════════════════════════════════════════════════
                    📄 Document Parser Interface
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Defines the abstract base class for all document parsers in the AAT system.
Provides a consistent interface for extracting text and images from various
document formats (Markdown, PDF, DOCX, etc.) used in test scenarios.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Parse a markdown file with embedded images
parser = MarkdownParser()
text, images = await parser.parse(Path("test_scenario.md"))

# Parse a PDF document
pdf_parser = PDFParser()
text, diagrams = await pdf_parser.parse(Path("spec.pdf"))
```

⚙️  CORE ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
    BaseParser (ABC)
         ├── parse()          → Extract text + images from document
         └── supported_extensions → List valid file extensions

    Implementation Pattern:
    MarkdownParser ──────────────┐
    PDFParser ───────────────────┤
    DocxParser ──────────────────┤── All implement BaseParser interface
    HTMLParser ──────────────────┘

    Parser Usage Flow:
    1. Check supported_extensions for file compatibility
    2. Call parse(file_path) to extract content
    3. Receive (text: str, images: list[bytes]) tuple
    4. Use extracted content for scenario generation or analysis

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- Abstract Parse Method: Defines signature for document parsing
- Extension Filtering: Validators check file compatibility before parsing
- Dual Extraction: Returns both text content and embedded images
- Type Safety: Uses Path objects for file system operations

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- All parse() methods are async - must use await when calling
- Image extraction varies by format (Markdown: ![]() refs, PDF: embedded)
- Unsupported extensions should raise ParserError, not return empty results
- Parsers must handle UTF-8 encoding errors gracefully

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Always check supported_extensions before calling parse()
- Handle ParserError exceptions for unsupported/corrupted files
- Validate Path exists before passing to parser
- Consider memory usage for large documents with many images

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ When you need to parse test scenarios from documentation
✅ When extracting requirements from spec documents
✅ When processing user-provided test descriptions
❌ Don't implement for binary formats without text extraction needs

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path  # noqa: TC003


class BaseParser(ABC):
    """Document parser abstract interface."""

    @abstractmethod
    async def parse(self, file_path: Path) -> tuple[str, list[bytes]]:
        """Parse document into (text, images).

        Args:
            file_path: Path to document file.

        Returns:
            Tuple of (extracted text, list of extracted image PNG bytes).
        """
        ...

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Supported file extensions: ['.md', '.txt']."""
        ...
