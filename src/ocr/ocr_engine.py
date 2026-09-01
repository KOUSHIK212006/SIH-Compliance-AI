"""Modular OCR engine for SIH-Compliance-AI.

Provides `init_reader` for reader reuse and `ocr_image_path` which
validates the image, applies configurable preprocessing, runs OCR via
EasyOCR (CPU by default), and returns structured, normalized results.
"""
from typing import List, Dict, Any, Optional, Tuple
import os
import time

try:
    import easyocr
except Exception:  # pragma: no cover - runtime import check
    easyocr = None

import cv2
import numpy as np


class OCRException(Exception):
    pass


# simple cache for created readers keyed by tuple(langs_tuple, gpu)
_readers: Dict[Tuple[str, ...], Any] = {}


def init_reader(langs: Optional[List[str]] = None, gpu: bool = False):
    """Initialize or return a cached EasyOCR Reader.

    Args:
        langs: list of language codes (default ['en']).
        gpu: whether to enable GPU for the reader (default False).

    Returns:
        An EasyOCR Reader instance.
    """
    if easyocr is None:
        raise OCRException("EasyOCR is not installed. Install it with: pip install easyocr")

    if langs is None:
        langs = ["en"]

    key = (tuple(langs), bool(gpu))
    reader = _readers.get(key)
    if reader is None:
        reader = easyocr.Reader(langs, gpu=gpu)
        _readers[key] = reader
    return reader


def _preprocess_image(img: np.ndarray, max_dim: int = 1800, clahe_clip: float = 3.0, clahe_grid: Tuple[int, int] = (8, 8), denoise_h: int = 10) -> Tuple[np.ndarray, float]:
    """Preprocess image for OCR and return (proc_image, scale).

    Scale is the factor new_dim / original_dim so callers can map
    coordinates back to the original image size.
    """
    # work on a copy
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape[:2]
    scale = 1.0
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Apply CLAHE
    if clahe_clip and clahe_grid:
        clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=clahe_grid)
        gray = clahe.apply(gray)

    # Denoise
    if denoise_h and denoise_h > 0:
        gray = cv2.fastNlMeansDenoising(gray, None, h=denoise_h)

    return gray, scale


def _normalize_confidence(conf: float) -> float:
    """Normalize confidence to 0.0 - 1.0 range.

    EasyOCR historically returns values in 0..1; however, handle cases
    where it's 0..100 by scaling down. Clamp to [0,1].
    """
    try:
        c = float(conf)
    except Exception:
        return 0.0
    if c > 1.5:
        c = c / 100.0
    # clamp
    if c < 0.0:
        c = 0.0
    if c > 1.0:
        c = 1.0
    return c


def _safe_extract_result_entry(r: Any):
    """Safely extract bbox, text, conf from a single EasyOCR result entry.

    Returns (bbox, text, conf) or None if malformed.
    """
    if not isinstance(r, (list, tuple)) or len(r) < 3:
        return None
    bbox, text, conf = r[0], r[1], r[2]
    # basic validations
    if not isinstance(bbox, (list, tuple)):
        return None
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            text = ""
    return bbox, text, conf


def ocr_image_path(image_path: str, langs: Optional[List[str]] = None, preprocess: bool = True, reader: Optional[Any] = None, *, max_dim: int = 1800, clahe_clip: float = 3.0, clahe_grid: Tuple[int, int] = (8, 8), denoise_h: int = 10, gpu: bool = False, debug: bool = False) -> Dict[str, Any]:
    """Run OCR on an image and return structured results.

    Backwards-compatible signature with additional optional parameters.
    """
    if langs is None:
        langs = ["en"]

    if not os.path.exists(image_path):
        raise OCRException(f"Image not found: {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        raise OCRException(f"OpenCV cannot read the image: {image_path}")

    orig_h, orig_w = img.shape[:2]

    if easyocr is None:
        raise OCRException("EasyOCR is not installed. Install it with: pip install easyocr")

    start_time = time.time()

    # prepare image for OCR
    img_for_ocr = img
    scale = 1.0
    if preprocess:
        proc, scale = _preprocess_image(img, max_dim=max_dim, clahe_clip=clahe_clip, clahe_grid=clahe_grid, denoise_h=denoise_h)
        # convert grayscale back to BGR for EasyOCR if needed
        if len(proc.shape) == 2:
            img_for_ocr = cv2.cvtColor(proc, cv2.COLOR_GRAY2BGR)
        else:
            img_for_ocr = proc

    # init or reuse reader
    if reader is None:
        reader = init_reader(langs, gpu=gpu)

    try:
        results = reader.readtext(img_for_ocr)
    except Exception as exc:
        raise OCRException(f"OCR processing failed: {exc}")

    parsed_details = []
    texts = []
    confs = []

    for r in results:
        out = _safe_extract_result_entry(r)
        if out is None:
            # skip malformed entry
            continue
        bbox_raw, text, conf_raw = out

        # bbox_raw is typically a list of four points [[x,y],...]
        try:
            pts = np.array(bbox_raw, dtype=float)
            xs = pts[:, 0]
            ys = pts[:, 1]
            x_min = float(np.min(xs))
            x_max = float(np.max(xs))
            y_min = float(np.min(ys))
            y_max = float(np.max(ys))
        except Exception:
            # fallback to bounding-box zeros
            x_min = y_min = x_max = y_max = 0.0

        # Map bbox back to original image coordinates if preprocessing resized image
        if scale and scale != 1.0:
            # coords are on scaled image -> divide by scale to map back
            try:
                x_min_orig = x_min / scale
                x_max_orig = x_max / scale
                y_min_orig = y_min / scale
                y_max_orig = y_max / scale
            except Exception:
                x_min_orig = x_min; x_max_orig = x_max; y_min_orig = y_min; y_max_orig = y_max
        else:
            x_min_orig = x_min; x_max_orig = x_max; y_min_orig = y_min; y_max_orig = y_max

        # normalized bbox relative to original image size
        try:
            nx0 = max(0.0, min(1.0, x_min_orig / float(orig_w)))
            ny0 = max(0.0, min(1.0, y_min_orig / float(orig_h)))
            nx1 = max(0.0, min(1.0, x_max_orig / float(orig_w)))
            ny1 = max(0.0, min(1.0, y_max_orig / float(orig_h)))
        except Exception:
            nx0 = ny0 = nx1 = ny1 = 0.0

        conf = _normalize_confidence(conf_raw)

        parsed = {
            "bbox": bbox_raw,
            "bbox_xyxy_orig": [x_min_orig, y_min_orig, x_max_orig, y_max_orig],
            "bbox_norm": [nx0, ny0, nx1, ny1],
            "text": text,
            "confidence": conf,
        }

        parsed_details.append(parsed)
        texts.append(text)
        confs.append(conf)

    full_text = "\n".join([t for t in texts if t])
    mean_conf = float(sum(confs) / len(confs)) if confs else None

    elapsed = time.time() - start_time
    if debug:
        print(f"OCR DEBUG: image={image_path}, orig_size=({orig_w}x{orig_h}), scale={scale:.4f}, detections={len(parsed_details)}, time={elapsed:.3f}s")

    return {
        "text": full_text,
        "details": parsed_details,
        "mean_confidence": mean_conf,
        "raw_results": results,
    }
