# Label Intelligence

`extract_label_fields(text)` converts plain OCR text into deterministic,
evidence-preserving label fields. It does not perform OCR or make regulatory,
health, or compliance decisions.

Each extracted field contains its value, source text, confidence, and the
pattern/header method used. Missing fields are returned as `None`. The design
uses `LabelFieldExtractor` so a future ML implementation can replace the
rule-based extractor without changing callers.
