"""
════════════════════════════════════════════════════════════════════════════════
                    📝 Markdown & Text Document Parser
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Concrete implementation of BaseParser for Markdown and plain text files.
Extracts text content and resolves image references from Markdown files,
providing structured data for test scenario generation and analysis.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Parse a test scenario document with screenshots
parser = MarkdownParser()
text, images = await parser.parse(Path("user_login_flow.md"))

# text contains full markdown content
# images contains PNG bytes from ![screenshot](images/step1.png) references

# Plain text files (no images)
text, empty_images = await parser.parse(Path("test_notes.txt"))
```

⚙️  CORE ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
    MarkdownParser extends BaseParser
         ├── supported_extensions: ['.md', '.txt']
         ├── parse() → Extract text + resolve ![](image) references
         └── Image resolution via relative paths

    Processing Flow:
    ┌─────────────────────────────────────────────────────────────────┐
    │ Input: .md/.txt file                                            │
    │                         ↓                                        │
    │ 1. Read file as UTF-8 text                                      │
    │                         ↓                                        │
    │ 2. If .txt → return (text, [])                                 │
    │    If .md  → continue to image extraction                       │
    │                         ↓                                        │
    │ 3. Find all ![alt](path) patterns via regex                    │
    │                         ↓                                        │
    │ 4. Resolve relative paths, read PNG bytes                      │
    │                         ↓                                        │
    │ 5. Return (text, list[bytes])                                  │
    └─────────────────────────────────────────────────────────────────┘

    Image Reference Pattern:
    ```markdown
    ![Login Screenshot](../screenshots/login.png)
     │              │                           │
     │              │                           └─ File resolved relative to .md file
     │              └────────────────────────────── Regex captured as image path
     └───────────────────────────────────────────── Ignored alt text
    ```

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- Dual Format Support: Handles both Markdown (.md) and plain text (.txt)
- Text Extraction: Reads full file content as UTF-8 string
- Image Reference Parsing: Uses regex to find ![](path) patterns
- Path Resolution: Converts relative image paths to absolute filesystem locations
- Graceful Missing Images: Logs warnings but continues when images not found
- Error Handling: Wraps OS errors in ParserError with context

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Only supports PNG image extraction (most common for screenshots)
- Image paths must be relative to the .md file location
- Missing images don't fail parsing - only log warnings
- Regex-based parsing (not full Markdown AST) - simple but not exhaustive
- No image format validation - assumes referenced files are valid PNGs

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Keep image paths relative to .md file for portability
- Use PNG format for screenshots (widely compatible)
- Place images in subdirectory near .md file (e.g., images/ or screenshots/)
- Check logs for warnings about missing referenced images
- Use absolute paths only when necessary (prefer relative)

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Parsing test scenario documentation with embedded screenshots
✅ Processing user-written test specifications in Markdown
✅ Extracting requirements from technical documentation
❌ Don't use for PDF, DOCX, or other binary formats
❌ Don't use when full Markdown AST parsing is required

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
import re
from pathlib import Path  # noqa: TC003

from aat.core.exceptions import ParserError
from aat.parsers.base import BaseParser

logger = logging.getLogger(__name__)

# Regex: ![alt text](image_path)
_IMAGE_REF_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


class MarkdownParser(BaseParser):
    """Parse markdown and plain-text files.

    Extracts text content and referenced images from ``![alt](path)`` patterns.
    """

    @property
    def supported_extensions(self) -> list[str]:
        """Supported file extensions."""
        return [".md", ".txt"]

    async def parse(self, file_path: Path) -> tuple[str, list[bytes]]:
        """Parse markdown/text file.

        Args:
            file_path: Path to the .md or .txt file.

        Returns:
            Tuple of (extracted text, list of referenced image bytes).

        Raises:
            ParserError: If the file cannot be read.
        """
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"Cannot read file: {file_path}"
            raise ParserError(msg) from exc

        # For .txt files, skip image extraction
        if file_path.suffix.lower() == ".txt":
            return text, []

        images: list[bytes] = []
        for match in _IMAGE_REF_RE.finditer(text):
            img_rel = match.group(1).strip()
            img_path = (file_path.parent / img_rel).resolve()
            try:
                img_bytes = img_path.read_bytes()
                images.append(img_bytes)
            except OSError:
                logger.warning("Referenced image not found, skipping: %s", img_path)

        return text, images
