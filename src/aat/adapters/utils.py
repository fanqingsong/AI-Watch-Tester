"""
════════════════════════════════════════════════════════════════════════════════
                  🔧 Adapter Utilities Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Shared helper functions for AI adapters. Provides common utilities for image
encoding, data transformation, and format conversion used across multiple
AI provider implementations.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```python
from aat.adapters.utils import encode_image_to_base64

# Encode screenshot for Vision API
screenshot_bytes = await engine.screenshot()
base64_image = encode_image_to_base64(screenshot_bytes)

# Use in API request
payload = {
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/png",
        "data": base64_image
    }
}
```

⚙️  AVAILABLE UTILITIES
───────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────────┐
│  Function               │  Purpose                          │
├────────────────────────────────────────────────────────────────────────────┤
│  encode_image_to_base64 │  Convert image bytes to base64     │
└────────────────────────────────────────────────────────────────────────────┘

📦 ENCODE_IMAGE_TO_BASE64
───────────────────────────────────────────────────────────────────────────────
Encodes raw image bytes to base64 string for API transmission:
• Input: Raw image bytes (PNG, JPEG, etc.)
• Output: Base64-encoded ASCII string
• Use Case: Vision API requests (Claude, OpenAI)
• Format: Standard base64 encoding (no URL-safe variants)

🔧 TECHNICAL DETAILS
───────────────────────────────────────────────────────────────────────────────
```python
# Encoding process
image_bytes = b"\x89PNG..."  # Raw image data
base64_string = base64.b64encode(image_bytes).decode("ascii")
# Result: "iVBORw0KGgo..." (base64 string)

# API usage
api_payload = f"data:image/png;base64,{base64_string}"
```

💡 DESIGN RATIONALE
───────────────────────────────────────────────────────────────────────────────
• Centralized encoding — Consistent implementation across all adapters
• Type safety — Clear input/output types with docstrings
• Error handling — Base64 encoding is reliable and predictable
• ASCII output — Ensures JSON compatibility for API payloads

⚠️  USAGE NOTES
───────────────────────────────────────────────────────────────────────────────
• Image format — Accepts any image format (PNG, JPEG, etc.)
• No validation — Assumes valid image data (caller's responsibility)
• No compression — Direct base64 encoding (no optimization)
• Memory usage — Full image loaded into memory during encoding

🎯 COMMON USE CASES
───────────────────────────────────────────────────────────────────────────────
1. Vision API Requests — Send screenshots to Claude/OpenAI for analysis
2. Document Analysis — Include images in scenario generation
3. Failure Analysis — Provide visual context for debugging
4. Step Verification — Screenshot-based validation

🔗 INTEGRATION
───────────────────────────────────────────────────────────────────────────────
Used by:
• ClaudeAdapter — Vision API for screenshot analysis
• OpenAIAdapter — Vision API for visual debugging
• Any adapter with vision capabilities

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import base64


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string.

    Args:
        image_bytes: Raw image data (PNG, JPEG, etc.).

    Returns:
        Base64-encoded string suitable for API payloads.

    Example:
        >>> data = b"\\x89PNG..."
        >>> encoded = encode_image_to_base64(data)
        >>> "data:image/png;base64," + encoded
    """
    return base64.b64encode(image_bytes).decode("ascii")


__all__ = [
    "encode_image_to_base64",
]
