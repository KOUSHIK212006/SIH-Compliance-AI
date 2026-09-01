"""Reusable ingredient parser for SIH-Compliance-AI.

This module contains lightweight, heuristic parsing of packaged-food
ingredient lists. It is intentionally simple and self-contained for
prototype use and testing; it does not call external services.
"""
import re
from typing import List, Dict, Any


def remove_ocr_letter_spacing(s: str) -> str:
    """Collapse OCR-style spaced letters: 's u g a r' -> 'sugar'."""
    return re.sub(r"(?:\b[A-Za-z]\s+){2,}[A-Za-z]\b", lambda m: m.group(0).replace(" ", ""), s)


def split_top_level_commas(s: str) -> List[str]:
    """Split string on commas not inside parentheses."""
    parts = []
    buf = []
    depth = 0
    for ch in s:
        if ch == '(':
            depth += 1
            buf.append(ch)
        elif ch == ')':
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == ',' and depth == 0:
            part = ''.join(buf).strip()
            if part:
                parts.append(part)
            buf = []
        else:
            buf.append(ch)
    last = ''.join(buf).strip()
    if last:
        parts.append(last)
    return parts


def parse_ingredients(text: str) -> Dict[str, Any]:
    """Parse an ingredient list string into structured ingredients and additives.

    Returns a dict with keys:
      - ingredients: list of dicts {name, sub_ingredients}
      - additives: list of additive codes found (E### or INS###)
    """
    if not text:
        return {"ingredients": [], "additives": []}

    s = text.strip()
    s = s.replace('\n', ' ')
    # First collapse OCR-style spaced letters so headers like
    # "I n g r e d i e n t s :" become "Ingredients :"
    s = remove_ocr_letter_spacing(s)
    # Remove common 'Ingredients' header variants, with optional colon and surrounding spaces
    s = re.sub(r"^\s*Ingredients?\s*:?\s*", '', s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", ' ', s)

    # Extract additive codes like E330 or INS 110
    additives = re.findall(r"\b(?:E|INS)\s*\d{2,3}\b", s, flags=re.IGNORECASE)
    additives = [a.replace(' ', '').upper() for a in additives]

    s_no_add = re.sub(r"\b(?:E|INS)\s*\d{2,3}\b", '', s, flags=re.IGNORECASE)

    items = split_top_level_commas(s_no_add)

    ingredients = []
    for item in items:
        it = item.strip().strip('.')
        if not it:
            continue
        m = re.match(r"^([^()]+)\((.*)\)$", it)
        if m:
            name = m.group(1).strip()
            sub_raw = m.group(2).strip()
            subs = [sp.strip().strip('.') for sp in split_top_level_commas(sub_raw) if sp.strip()]
        else:
            name = it
            subs = []

        name = re.sub(r"\bcontains\b.*$,?", '', name, flags=re.IGNORECASE).strip()

        ingredients.append({"name": name, "sub_ingredients": subs})

    return {"ingredients": ingredients, "additives": additives}


__all__ = ["parse_ingredients"]
