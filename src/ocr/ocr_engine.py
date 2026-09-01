"""Modular OCR engine for SIH-Compliance-AI.

Implements `ocr_image_path` which validates the image, applies lightweight
preprocessing, runs OCR via EasyOCR, and returns structured results.
"""
from typing import List, Dict, Any, Optional
import os

try:
    import easyocr
except Exception:  # pragma: no cover - runtime import check
    easyocr = None

import cv2
import numpy as np


class OCRException(Exception):
    pass


def _preprocess_image(img: np.ndarray, max_dim: int = 1800) -> np.ndarray:
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize if too large to speed up OCR
    h, w = gray.shape[:2]
    scale = 1.0
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # Apply CLAHE to improve local contrast (helps with product labels)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, None, h=10)

    return gray


def ocr_image_path(image_path: str, langs: Optional[List[str]] = None, preprocess: bool = True) -> Dict[str, Any]:
    """Run OCR on an image file and return structured results.

    Args:
        image_path: path to the image file.
        langs: list of language codes for EasyOCR (default ['en']).
        preprocess: whether to run basic preprocessing (CLAHE, denoise, resize).

    Returns:
        dict with keys: 'text' (str), 'details' (list of detections),
        'mean_confidence' (float|None), and 'raw_results' (EasyOCR output).

    Raises:
        OCRException on missing files, unreadable images, missing dependency, or OCR failure.
    """
    if langs is None:
        langs = ["en"]

    if not os.path.exists(image_path):
        raise OCRException(f"Image not found: {image_path}")

    # Validate image readability
    img = cv2.imread(image_path)
    if img is None:
        raise OCRException(f"OpenCV cannot read the image: {image_path}")

    if easyocr is None:
        raise OCRException("EasyOCR is not installed. Install it with: pip install easyocr")

    try:
        img_for_ocr = img
        if preprocess:
            proc = _preprocess_image(img)
            # EasyOCR accepts numpy arrays (grayscale or BGR); convert back to 3-channel
            if len(proc.shape) == 2:
                img_for_ocr = cv2.cvtColor(proc, cv2.COLOR_GRAY2BGR)
            else:
                img_for_ocr = proc

        # Instantiate reader with CPU only to avoid GPU assumptions
        reader = easyocr.Reader(langs, gpu=False)

        # Pass numpy image directly to readtext to avoid extra disk I/O
        results = reader.readtext(img_for_ocr)

        texts = [r[1] for r in results]
        confs = [float(r[2]) for r in results]

        details = [
            {"bbox": r[0], "text": r[1], "confidence": float(r[2])}
            for r in results
        ]

        full_text = "\n".join(texts)
        mean_conf = float(sum(confs) / len(confs)) if confs else None

        return {
            "text": full_text,
            "details": details,
            "mean_confidence": mean_conf,
            "raw_results": results,
        }

    except Exception as exc:
        raise OCRException(f"OCR processing failed: {exc}")
