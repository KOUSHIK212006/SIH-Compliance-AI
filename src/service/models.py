"""Structured result model for the unified analysis service."""
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AnalysisResult:
    """Complete analysis output assembled from existing backend modules."""

    ocr_result: Dict[str, Any]
    ocr_text: str
    product: Dict[str, Any]
    pipeline_result: Dict[str, Any]
    label_fields: Dict[str, Any]
    ingredients: List[Any]
    normalized_ingredients: List[Dict[str, Any]]
    compliance_findings: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    decision: Dict[str, Any]
    explanations: List[Dict[str, Any]]
    trace: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str)
