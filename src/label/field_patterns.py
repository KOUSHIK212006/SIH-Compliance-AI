"""Deterministic header and value patterns for food-label extraction."""
import re


FIELD_HEADERS = {
    "ingredients": r"i\s*n\s*g\s*r\s*e\s*d\s*i\s*e\s*n\s*t\s*s?",
    "net_quantity": r"net\s*(?:wt|weight|quantity)|net\s*qty",
    "serving_size": r"serving\s*size|serving",
    "allergen_information": r"allergen(?:s)?(?:\s+information)?|may\s+contain|contains",
    "veg_nonveg_indicator": r"veg(?:etarian)?|non[- ]?veg(?:etarian)?",
    "fssai_license": r"fssai(?:\s+licen[cs]e)?|licen[cs]e\s*no",
    "batch_number": r"batch(?:\s*(?:no|number))?|lot(?:\s*(?:no|number))?",
    "manufacturing_date": r"(?:mfg|manufactur(?:ed|ing))\s*date|date\s*of\s*manufactur(?:e|ing)",
    "expiry_date": r"exp(?:iry|ires?)\s*date|use\s*by",
    "best_before": r"best\s*before",
    "country_of_origin": r"country\s*of\s*origin|made\s*in",
}

DATE_PATTERN = r"\b(?:\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{4}[/.\-]\d{1,2}[/.\-]\d{1,2})\b"
QUANTITY_PATTERN = r"\b\d+(?:\.\d+)?\s*(?:kg|g|mg|l|ml|cl|oz|lb)\b"
FSSAI_PATTERN = r"\b\d{14}\b"
FIELD_ORDER = list(FIELD_HEADERS)
