"""OCR helper for screenshot text extraction (EXEC-7).

Consolidates the three pytesseract call sites that previously inlined their
own decode + OpenCV preprocessing inside ``StepExecutor``:

- ``_check_target_visible`` — Otsu threshold (pass A) and raw grayscale
  sparse-text (pass B); both ``kor+eng``.
- ``_verify_post_step`` — CLAHE contrast enhancement; ``kor+eng``, psm 6.
- ``_verify_text_on_screen`` — CLAHE + 2x upscale; default language, psm
  unspecified (``--oem 3`` only).

Each call site passes its **original** decode/preprocess/psm/oem/lang config
and receives byte-for-byte identical output, because the preprocessing
sequence is reproduced exactly:

================  =====================  =========  =======  =====
call site         preprocess            lang       oem      psm
================  =====================  =========  =======  =====
check_visible A   "otsu"                "kor+eng"  3        6
check_visible B   "raw"                 "kor+eng"  3        11
verify_post_step  "clahe"               "kor+eng"  3        6
verify_text       "clahe_upscale2x"     (default)  3        None
================  =====================  =========  =======  =====

Note: the ``"otsu"`` / ``"raw"`` paths decode with ``IMREAD_COLOR`` then
``cvtColor(BGR2GRAY)`` — *not* ``IMREAD_GRAYSCALE`` — matching the original
``_check_target_visible`` implementation exactly (OpenCV's two grayscale
conversions are not numerically identical).
"""

from __future__ import annotations

from typing import Final

import cv2
import numpy as np
import pytesseract  # type: ignore[import-untyped]

#: Preprocessing strategies supported by :func:`ocr_screenshot`.
Preprocess = str

#: No preprocessing — return the decoded grayscale image unchanged.
PREPROCESS_RAW: Final[str] = "raw"
#: Otsu binary thresholding (``THRESH_BINARY + THRESH_OTSU``).
PREPROCESS_OTSU: Final[str] = "otsu"
#: CLAHE contrast limited adaptive histogram equalization (clip 3.0, 8x8 tile).
PREPROCESS_CLAHE: Final[str] = "clahe"
#: CLAHE followed by a 2x bicubic upscale (Canvas-text optimisation).
PREPROCESS_CLAHE_UPSCALE2X: Final[str] = "clahe_upscale2x"

#: Module-level defaults — match the most common historical call config
#: (``kor+eng``, oem 3, psm 6) so callers that omit a value still get the
#: legacy behaviour.
DEFAULT_LANG: Final[str] = "kor+eng"
DEFAULT_OEM: Final[int] = 3
DEFAULT_PSM: Final[int] = 6


def _build_config(oem: int | None, psm: int | None) -> str:
    """Assemble the ``--config`` string passed to pytesseract.

    Replicates the legacy string formatting:
    - ``_check_target_visible`` / ``_verify_post_step`` used ``"--oem 3 --psm N"``
    - ``_verify_text_on_screen`` used ``"--oem 3"`` (no ``--psm``)
    """
    parts: list[str] = []
    if oem is not None:
        parts.append(f"--oem {oem}")
    if psm is not None:
        parts.append(f"--psm {psm}")
    return " ".join(parts)


def ocr_screenshot(
    image: bytes,
    *,
    lang: str | None = DEFAULT_LANG,
    psm: int | None = DEFAULT_PSM,
    oem: int | None = DEFAULT_OEM,
    preprocess: str = PREPROCESS_CLAHE,
) -> str:
    """Run pytesseract on a screenshot after the requested preprocessing.

    Args:
        image: PNG-encoded screenshot bytes.
        lang: Tesseract language pack(s), e.g. ``"kor+eng"``. Defaults to
            :data:`DEFAULT_LANG`. Pass ``None`` to omit ``lang`` entirely so
            pytesseract falls back to its own default (this matches the legacy
            ``_verify_text_on_screen`` call which did not pass ``lang``).
        psm: Tesseract page-segmentation mode. ``None`` omits ``--psm``
            (matches ``_verify_text_on_screen`` which used ``"--oem 3"`` only).
        oem: Tesseract OCR engine mode. ``None`` omits ``--oem``.
        preprocess: One of :data:`PREPROCESS_RAW`, :data:`PREPROCESS_OTSU`,
            :data:`PREPROCESS_CLAHE`, :data:`PREPROCESS_CLAHE_UPSCALE2X`.

    Returns:
        The recognized text, exactly as ``pytesseract.image_to_string`` returns
        it for the equivalent legacy configuration.
    """
    arr = np.frombuffer(image, dtype=np.uint8)

    # ``otsu`` and ``raw`` historically decoded COLOR then converted to gray
    # (cvtColor), whereas the CLAHE paths decoded directly to grayscale.
    processed: np.ndarray
    if preprocess == PREPROCESS_OTSU:
        img_color = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img_color is None:
            return ""
        gray_img = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
        _, processed = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif preprocess == PREPROCESS_RAW:
        img_color = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img_color is None:
            return ""
        processed = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
    else:
        decoded = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if decoded is None:
            return ""
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        processed = clahe.apply(decoded)
        if preprocess == PREPROCESS_CLAHE_UPSCALE2X:
            h, w = processed.shape
            processed = cv2.resize(processed, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        elif preprocess != PREPROCESS_CLAHE:
            # Unknown strategy → fall back to plain CLAHE (safe default that
            # still yields a valid image for OCR; preserves the "no crash"
            # contract). This branch is never hit by the routed call sites.
            pass

    config = _build_config(oem, psm)
    if lang is None:
        text: str = pytesseract.image_to_string(processed, config=config)
    else:
        text = pytesseract.image_to_string(processed, lang=lang, config=config)
    return text


__all__ = [
    "DEFAULT_LANG",
    "DEFAULT_OEM",
    "DEFAULT_PSM",
    "PREPROCESS_CLAHE",
    "PREPROCESS_CLAHE_UPSCALE2X",
    "PREPROCESS_OTSU",
    "PREPROCESS_RAW",
    "ocr_screenshot",
]
