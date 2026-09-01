"""Simple, modular OCR component using EasyOCR.

Provides a single function `ocr_image_path` that accepts an image path,
runs OCR, and returns extracted text plus confidence details.

This module deliberately avoids installing or changing the project's
existing PyTorch/OpenCV/Ultralytics setup; it uses EasyOCR (which uses
the existing PyTorch installation) and OpenCV for image loading.
"""
from typing import List, Dict, Any, Optional
import os

try:
    import easyocr
except Exception:  # pragma: no cover - runtime import check
    easyocr = None

import cv2


class OCRException(Exception):
    pass


def ocr_image_path(image_path: str, langs: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run OCR on an image file and return text and confidences.

    Args:
        image_path: Path to an image file.
        langs: Optional list of language codes for OCR (default ['en']).

    Returns:
        A dict with keys: 'text' (str), 'details' (list of detections),
        and 'mean_confidence' (float|None).

    Raises:
        OCRException: for missing files, missing dependency, or processing errors.
    """
    if langs is None:
        langs = ["en"]

    if not os.path.exists(image_path):
        raise OCRException(f"Image not found: {image_path}")

    # Read image with OpenCV first to validate
    img = cv2.imread(image_path)
    if img is None:
        raise OCRException(f"Failed to read image (cv2.imread returned None): {image_path}")

    if easyocr is None:
        raise OCRException(
            "EasyOCR is not installed. Install it with: pip install easyocr"
        )

    try:
        # Create reader; force CPU mode to avoid GPU assumptions
        reader = easyocr.Reader(langs, gpu=False)
        results = reader.readtext(image_path)

        texts = [r[1] for r in results]
        confs = [float(r[2]) for r in results]

        details = [
            {"bbox": r[0], "text": r[1], "confidence": float(r[2])}
            for r in results
        ]

        full_text = "\n".join(texts)
        mean_conf = float(sum(confs) / len(confs)) if confs else None

        return {"text": full_text, "details": details, "mean_confidence": mean_conf}

    except Exception as exc:
        raise OCRException(f"OCR processing failed: {exc}")
