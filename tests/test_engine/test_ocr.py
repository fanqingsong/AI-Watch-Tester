"""Tests for the OCR screenshot helper (EXEC-7).

pytesseract is mocked so the tests run without a real Tesseract binary; they
verify that :func:`aat.engine.ocr.ocr_screenshot` selects the correct
preprocessing branch and forwards the right lang/oem/psm config to
``image_to_string`` for each of the three legacy call-site configurations.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from aat.engine import ocr as ocr_module
from aat.engine.ocr import (
    DEFAULT_LANG,
    DEFAULT_OEM,
    DEFAULT_PSM,
    PREPROCESS_CLAHE,
    PREPROCESS_CLAHE_UPSCALE2X,
    PREPROCESS_OTSU,
    PREPROCESS_RAW,
    ocr_screenshot,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _png(width: int = 60, height: int = 40, value: int = 200) -> bytes:
    """A grayscale PNG image of uniform brightness."""
    img = np.full((height, width), value, dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok  # noqa: S101
    return bytes(buf)


def _png_color(width: int = 60, height: int = 40) -> bytes:
    """A color PNG image (3-channel) of uniform brightness."""
    img = np.full((height, width, 3), 200, dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok  # noqa: S101
    return bytes(buf)


# ── defaults ─────────────────────────────────────────────────────────────────


class TestDefaults:
    def test_defaults_match_legacy_common_config(self) -> None:
        """Module defaults reproduce the most common legacy config."""
        assert DEFAULT_LANG == "kor+eng"
        assert DEFAULT_OEM == 3
        assert DEFAULT_PSM == 6


# ── preprocessing branches ──────────────────────────────────────────────────


class TestPreprocessSelection:
    @patch("aat.engine.ocr.pytesseract")
    def test_otsu_branch_thresholds_the_image(self, mock_tess: MagicMock) -> None:
        """The 'otsu' branch applies Otsu thresholding before OCR."""
        mock_tess.image_to_string.return_value = "ok"
        before_dim = None

        ocr_screenshot(_png(), preprocess=PREPROCESS_OTSU, lang="kor+eng", oem=3, psm=6)

        passed_image = mock_tess.image_to_string.call_args.args[0]
        # Otsu on a uniform-brightness image yields a binary (0/255) image.
        unique = {int(v) for v in np.unique(passed_image)}
        assert unique.issubset({0, 255})

    @patch("aat.engine.ocr.pytesseract")
    def test_raw_branch_returns_grayscale(self, mock_tess: MagicMock) -> None:
        """The 'raw' branch forwards the unmodified grayscale image."""
        mock_tess.image_to_string.return_value = "ok"

        ocr_screenshot(_png_color(), preprocess=PREPROCESS_RAW, lang="kor+eng", oem=3, psm=11)

        passed_image = mock_tess.image_to_string.call_args.args[0]
        # Raw converts COLOR→gray; a uniform (200,200,200) image stays ~200.
        assert passed_image.ndim == 2
        assert int(passed_image[0, 0]) == 200

    @patch("aat.engine.ocr.pytesseract")
    def test_clahe_upscale_doubles_dimensions(self, mock_tess: MagicMock) -> None:
        """The 'clahe_upscale2x' branch doubles both image dimensions."""
        mock_tess.image_to_string.return_value = "ok"
        png = _png(width=60, height=40)

        ocr_screenshot(
            png,
            preprocess=PREPROCESS_CLAHE_UPSCALE2X,
            lang=None,
            oem=3,
            psm=None,
        )

        passed_image = mock_tess.image_to_string.call_args.args[0]
        h, w = passed_image.shape
        assert (w, h) == (120, 80)

    @patch("aat.engine.ocr.pytesseract")
    def test_clahe_branch_keeps_original_dimensions(self, mock_tess: MagicMock) -> None:
        """The 'clahe' branch preserves the input dimensions."""
        mock_tess.image_to_string.return_value = "ok"
        png = _png(width=60, height=40)

        ocr_screenshot(png, preprocess=PREPROCESS_CLAHE, lang="kor+eng", oem=3, psm=6)

        passed_image = mock_tess.image_to_string.call_args.args[0]
        h, w = passed_image.shape
        assert (w, h) == (60, 40)


# ── config forwarding ───────────────────────────────────────────────────────


class TestConfigForwarding:
    @patch("aat.engine.ocr.pytesseract")
    def test_psm_and_oem_assembled_into_config(self, mock_tess: MagicMock) -> None:
        """Both --oem and --psm appear in the config string."""
        mock_tess.image_to_string.return_value = "ok"

        ocr_screenshot(_png(), lang="kor+eng", oem=3, psm=6, preprocess=PREPROCESS_CLAHE)

        kwargs = mock_tess.image_to_string.call_args.kwargs
        assert kwargs["lang"] == "kor+eng"
        assert "--oem 3" in kwargs["config"]
        assert "--psm 6" in kwargs["config"]

    @patch("aat.engine.ocr.pytesseract")
    def test_psm_none_omits_psm_flag(self, mock_tess: MagicMock) -> None:
        """psm=None omits --psm (matches _verify_text_on_screen)."""
        mock_tess.image_to_string.return_value = "ok"

        ocr_screenshot(_png(), lang=None, oem=3, psm=None, preprocess=PREPROCESS_CLAHE)

        kwargs = mock_tess.image_to_string.call_args.kwargs
        assert kwargs["config"] == "--oem 3"
        assert "--psm" not in kwargs["config"]
        # lang=None → kwarg omitted entirely
        assert "lang" not in kwargs

    @patch("aat.engine.ocr.pytesseract")
    def test_returns_image_to_string_output_unchanged(self, mock_tess: MagicMock) -> None:
        """The helper returns pytesseract's output verbatim."""
        mock_tess.image_to_string.return_value = "recognized text\n"

        result = ocr_screenshot(_png(), preprocess=PREPROCESS_CLAHE)

        assert result == "recognized text\n"


# ── robustness ──────────────────────────────────────────────────────────────


class TestRobustness:
    def test_undecodable_image_returns_empty_string(self) -> None:
        """Garbage bytes do not raise; an empty string is returned."""
        result = ocr_screenshot(b"not an image", preprocess=PREPROCESS_CLAHE)

        assert result == ""

    def test_unknown_preprocess_falls_back_to_clahe(self) -> None:
        """An unknown preprocess string does not crash."""
        with patch.object(ocr_module, "pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "ok"
            # Should not raise even though "weird" is not a known strategy.
            result = ocr_screenshot(_png(), preprocess="weird")

        assert result == "ok"
