"""Rule-based extraction of structured fields from plain OCR text."""
import re
from typing import Dict, List, Optional, Tuple

from .field_patterns import DATE_PATTERN, FIELD_HEADERS, FIELD_ORDER, FSSAI_PATTERN, QUANTITY_PATTERN
from .models import ExtractedField, LabelExtractionResult


class LabelExtractionError(TypeError):
    """Raised when label OCR input is not text."""


_STOP_HEADERS = re.compile(
    r"^\s*(?:nutrition|nutritional|allergen|contains|manufactured|marketed|distributed|"
    r"storage|directions?|instructions?|net\s*(?:wt|weight|quantity)|serving|fssai|"
    r"batch|lot|mfg|manufacturing|expiry|best\s*before|country\s*of\s*origin|made\s*in)\b",
    re.IGNORECASE,
)


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))


def _header_match(line: str, field_name: str) -> Optional[re.Match[str]]:
    return re.search(r"^\s*(?P<header>" + FIELD_HEADERS[field_name] + r")\s*(?P<separator>[:.\-]?)[ \t]*(?P<value>.*)$", line, re.IGNORECASE)


def _field(name: str, value: str, source: str, method: str, confidence: float) -> ExtractedField:
    return ExtractedField(name=name, value=value.strip(), source_text=source, confidence=confidence, method=method)


def _find_value(lines: List[str], field_name: str, pattern: Optional[str] = None) -> Optional[ExtractedField]:
    for index, line in enumerate(lines):
        match = _header_match(line, field_name)
        if not match:
            continue
        value = match.group("value").strip()
        source = line
        if not value and index + 1 < len(lines) and not _STOP_HEADERS.match(lines[index + 1]):
            value = lines[index + 1].strip()
            source = f"{line}\n{lines[index + 1]}"
        if pattern:
            found = re.search(pattern, value, re.IGNORECASE)
            if not found:
                continue
            value = found.group(0)
        if value:
            return _field(field_name, value, source, f"header:{field_name}", 0.95 if match.group("separator") else 0.90)
    return None


def _extract_ingredients(lines: List[str]) -> Optional[ExtractedField]:
    for index, line in enumerate(lines):
        match = _header_match(line, "ingredients")
        if not match:
            continue
        values = []
        first = match.group("value").strip()
        if first:
            values.append(first)
        for following in lines[index + 1:]:
            if _STOP_HEADERS.match(following):
                break
            if following:
                values.append(following)
        value = " ".join(values).strip(" :-")
        if value:
            return _field("ingredients", value, "\n".join(lines[index:index + len(values) + 1]), "header:ingredients_until_next_section", 0.95)
        return None
    return None


def extract_label_fields(text: str) -> LabelExtractionResult:
    """Extract known label fields from OCR text with field-level evidence."""
    if not isinstance(text, str):
        raise LabelExtractionError("label OCR input must be a string")
    lines = _normalize_text(text).split("\n")
    fields: Dict[str, Optional[ExtractedField]] = {name: None for name in FIELD_ORDER}
    fields["ingredients"] = _extract_ingredients(lines)
    fields["net_quantity"] = _find_value(lines, "net_quantity", QUANTITY_PATTERN)
    fields["serving_size"] = _find_value(lines, "serving_size")
    fields["allergen_information"] = _find_value(lines, "allergen_information")
    fields["veg_nonveg_indicator"] = _find_value(lines, "veg_nonveg_indicator")
    fields["fssai_license"] = _find_value(lines, "fssai_license", FSSAI_PATTERN)
    fields["batch_number"] = _find_value(lines, "batch_number")
    fields["manufacturing_date"] = _find_value(lines, "manufacturing_date", DATE_PATTERN)
    fields["expiry_date"] = _find_value(lines, "expiry_date", DATE_PATTERN)
    fields["best_before"] = _find_value(lines, "best_before")
    fields["country_of_origin"] = _find_value(lines, "country_of_origin")
    warnings = []
    if not fields["ingredients"]:
        warnings.append("Ingredients field not found")
    return LabelExtractionResult(fields=fields, warnings=warnings)


class LabelFieldExtractor:
    """Replaceable object interface for deterministic label extraction."""

    def extract(self, text: str) -> LabelExtractionResult:
        return extract_label_fields(text)


__all__ = ["LabelExtractionError", "LabelFieldExtractor", "extract_label_fields"]
