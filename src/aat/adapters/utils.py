"""Adapter utilities.

Shared helper functions for AI adapters.
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
