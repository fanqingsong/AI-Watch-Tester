"""
════════════════════════════════════════════════════════════════════════════════
                🖼️ Image Processing Utilities Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Shared image processing utilities providing common functions for all matchers.
Eliminates code duplication across TemplateMatcher, FeatureMatcher, OCRMatcher,
and other vision-based components by centralizing image decoding and conversion logic.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
# Decode screenshot bytes for OpenCV processing
screenshot_bytes = Path("screenshot.png").read_bytes()
img_bgr = ImageUtils.decode_image(screenshot_bytes)
img_gray = ImageUtils.to_gray(img_bgr)

# Works with both bytes and file paths
img_bgr = ImageUtils.decode_image(Path("template.png"))
```

⚙️  IMAGE FORMAT CONVERSION PIPELINE
───────────────────────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Input Sources                                       │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐      │
│  │  PNG/JPEG Bytes    │  │  File Path (Path)  │  │  File Path (str)   │      │
│  │  screenshot_bytes │  │  Path("img.png")   │  │  "/path/to/img"    │      │
│  └────────┬───────────┘  └────────┬───────────┘  └────────┬───────────┘      │
└───────────┼───────────────────────┼───────────────────────┼──────────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                   ImageUtils.decode_image()                                  │
│  • np.frombuffer() for bytes • cv2.imread() for paths                        │
│  • cv2.imdecode() for PNG/JPEG decoding                                       │
│  • Returns: numpy.ndarray (BGR format)                                        │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         OpenCV Processing                                     │
│              Template matching, ORB detection, OCR preprocessing              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    ImageUtils.to_gray()                                       │
│  • Check dimensions: 2 channels = already grayscale                          │
│  • 3 channels = BGR → cv2.cvtColor(BGR2GRAY)                                  │
│  • Returns: numpy.ndarray (single channel grayscale)                         │
└──────────────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
• decode_image(): Universal decoder for bytes and file paths
  - Handles PNG, JPEG, and other formats supported by OpenCV
  - Returns BGR color format (OpenCV's default)
  - Raises ValueError on decoding failure with clear error message

• to_gray(): Smart grayscale conversion
  - Idempotent: returns original if already grayscale
  - Converts BGR to grayscale using cv2.COLOR_BGR2GRAY
  - Used by template matching, ORB, OCR preprocessing

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
• Only supports formats decodeable by OpenCV (PNG, JPEG, BMP, TIFF, WebP, etc.)
• decode_image() returns BGR format (not RGB) - this is OpenCV's default
• No alpha channel preservation - transparent backgrounds become black
• No validation of image dimensions - extremely large images may cause memory issues
• No exif/metadata handling - images are decoded as-is

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
1. Always call decode_image() before any OpenCV operations
2. Use to_gray() before template matching, ORB, or OCR (they require grayscale)
3. Handle ValueError exceptions from decode_image() for corrupt files
4. For web scraping, save screenshots as PNG bytes first, then decode
5. Memory management: OpenCV handles numpy arrays without explicit cleanup

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ GOOD USE CASES:
  • Preparing screenshots for template matching, ORB, or OCR
  • Loading reference templates from disk for matcher initialization
  • Converting between color spaces for OpenCV operations
  • Normalizing image inputs from different sources (files vs bytes)

❌ BAD USE CASES:
  • Direct image manipulation (use OpenCV functions directly)
  • Image format conversion (use Pillow/PIL for advanced format support)
  • Video processing (use cv2.VideoCapture instead)
  • GPU-accelerated processing (use cv2.cuda modules)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class ImageUtils:
    """Shared image processing utilities."""

    @staticmethod
    def decode_image(raw: bytes | Path) -> np.ndarray:
        """Decode image bytes or file path into a numpy array (BGR).

        Args:
            raw: Image as bytes (PNG/JPEG) or file path.

        Returns:
            numpy array in BGR color format.

        Raises:
            ValueError: If image decoding fails.
        """
        if isinstance(raw, Path | str):
            # Load from file path
            img = cv2.imread(str(raw), cv2.IMREAD_COLOR)
        else:
            # Decode from bytes
            arr = np.frombuffer(raw, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if img is None:
            msg = "Failed to decode image"
            raise ValueError(msg)
        return img

    @staticmethod
    def to_gray(img: np.ndarray) -> np.ndarray:
        """Convert image to grayscale if needed.

        Args:
            img: BGR or grayscale image.

        Returns:
            Grayscale image (single channel).
        """
        if len(img.shape) == 2:
            return img
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
