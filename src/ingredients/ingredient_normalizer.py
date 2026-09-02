"""Deterministic normalization for parsed ingredient values."""
import re
from typing import Any, Dict, List


_ADDITIVE_CODE_PATTERN = re.compile(r"^(E|INS)\s*-?\s*(\d{2,3})$", re.IGNORECASE)


def normalize_ingredient(value: str) -> Dict[str, Any]:
    """Normalize one ingredient or additive code.

    Non-string values raise ``TypeError``. Empty or whitespace-only strings
    return an ``invalid`` record so callers can handle them consistently.
    Meaningful spaces inside ingredient names are preserved.
    """
    if not isinstance(value, str):
        raise TypeError("ingredient value must be a string")

    cleaned = re.sub(r"\s+", " ", value.strip())
    if not cleaned:
        return {
            "raw": value,
            "canonical_name": "",
            "ingredient_type": "invalid",
            "additive_code": None,
        }

    additive_match = _ADDITIVE_CODE_PATTERN.fullmatch(cleaned)
    if additive_match:
        prefix, number = additive_match.groups()
        additive_code = f"{prefix.upper()}{number}"
        return {
            "raw": value,
            "canonical_name": additive_code,
            "ingredient_type": "additive_code",
            "additive_code": additive_code,
        }

    canonical_name = cleaned.casefold()
    return {
        "raw": value,
        "canonical_name": canonical_name,
        "ingredient_type": "ingredient",
        "additive_code": None,
    }


def normalize_ingredients(values: List[str]) -> List[Dict[str, Any]]:
    """Normalize a list while preserving order, duplicates, and raw values."""
    if not isinstance(values, list):
        raise TypeError("ingredient values must be a list")
    return [normalize_ingredient(value) for value in values]


__all__ = ["normalize_ingredient", "normalize_ingredients"]
