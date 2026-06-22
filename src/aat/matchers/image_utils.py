"""Shared image processing utilities for matchers.

This module contains common image processing functions used across
multiple matchers (TemplateMatcher, FeatureMatcher, etc.) to avoid
code duplication.
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
