"""Structured models for extracted food-label fields."""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExtractedField:
    name: str
    value: str
    source_text: str
    confidence: float
    method: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LabelExtractionResult:
    fields: Dict[str, Optional[ExtractedField]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fields": {
                name: value.to_dict() if value is not None else None
                for name, value in self.fields.items()
            },
            "warnings": list(self.warnings),
        }
