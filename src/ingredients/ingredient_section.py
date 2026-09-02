"""Locate and extract ingredient sections from noisy OCR text."""
import re
from typing import Any, Dict, Optional


_HEADER = re.compile(
    r"(?P<header>"
    r"(?:i\s*n\s*g\s*r\s*e\s*d\s*i\s*e\s*n\s*t\s*s?|"
    r"c\s*o\s*m\s*p\s*o\s*s\s*i\s*t\s*i\s*o\s*n|"
    r"m\s*a\s*d\s*e\s+with)"
    r"\s*(?::|-)?\s*(?:include|includes|used)?\s*(?=[^\w]|$))",
    re.IGNORECASE,
)
_STOP_LINE = re.compile(
    r"^\s*(?:nutrition\s*facts?|nutritional\s+information|allergen(?:s)?(?:\s+information)?|"
    r"may\s+contain|contains|manufactured\s+by|marketed\s+by|distributed\s+by|storage|"
    r"directions?|instructions?|net\s+weight|mrp|batch(?:\s+no)?|best\s+before|expiry|"
    r"fssai|customer\s+care|address|barcode)\b\s*:?[\s-]*",
    re.IGNORECASE,
)
_STOP_INLINE = re.compile(
    r"\s+(?=(?:nutrition\s*facts?|nutritional\s+information|allergen(?:s)?(?:\s+information)?|"
    r"may\s+contain|manufactured\s+by|marketed\s+by|distributed\s+by|storage|directions?|"
    r"instructions?|net\s+weight|mrp|batch(?:\s+no)?|best\s+before|expiry|fssai|customer\s+care|"
    r"address|barcode)\b\s*:?)",
    re.IGNORECASE,
)


def normalize_ocr_text(text: str) -> str:
    """Normalize line endings and repeated horizontal whitespace only."""
    if not isinstance(text, str):
        raise TypeError("OCR text must be a string")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))


def _header_is_plausible(text: str, match: re.Match[str]) -> bool:
    start = match.start()
    prefix = text[:start]
    if prefix and prefix[-1] not in "\n;|.!?":
        return False
    return True


def _not_found(warning: str = "Ingredient section not found") -> Dict[str, Any]:
    return {"found": False, "header": "", "raw_text": "", "confidence": 0.0, "start_index": None, "end_index": None, "warnings": [warning]}


def extract_ingredient_section(text: str) -> Dict[str, Any]:
    """Extract the first plausible ingredient section from OCR text."""
    if not isinstance(text, str):
        return _not_found("OCR text must be a string")
    normalized = normalize_ocr_text(text)
    if not normalized.strip():
        return _not_found()

    match: Optional[re.Match[str]] = None
    for candidate in _HEADER.finditer(normalized):
        if _header_is_plausible(normalized, candidate):
            match = candidate
            break
    if match is None:
        return _not_found()

    start = match.end()
    remainder = normalized[start:]
    stop_positions = []
    for line_match in re.finditer(r"(?:^|\n)([^\n]*)", remainder):
        if _STOP_LINE.match(line_match.group(1)):
            stop_positions.append(line_match.start(1))
    inline_match = _STOP_INLINE.search(remainder)
    if inline_match:
        stop_positions.append(inline_match.start())

    end = start + min(stop_positions) if stop_positions else len(normalized)
    candidate_text = normalized[start:end]
    raw_text = candidate_text.strip(" \t\n:-")
    raw_start = start + len(candidate_text) - len(candidate_text.lstrip(" \t\n:-"))
    raw_end = raw_start + len(raw_text)
    warnings = []
    confidence = 0.9 if stop_positions else 0.95
    if not raw_text:
        confidence = 0.3
        warnings.append("Ingredient section is empty")
    return {"found": True, "header": re.sub(r"\s+", " ", match.group("header")).strip(), "raw_text": raw_text, "confidence": confidence, "start_index": raw_start, "end_index": raw_end, "warnings": warnings}


__all__ = ["normalize_ocr_text", "extract_ingredient_section"]
