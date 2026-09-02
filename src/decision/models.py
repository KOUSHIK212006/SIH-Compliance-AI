"""Data models for evidence-backed product assessments."""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IngredientAssessment:
    ingredient: str
    normalized_name: str
    category: Optional[str]
    function: Optional[str]
    additive_code: Optional[str]
    rule_results: List[Dict[str, Any]] = field(default_factory=list)
    health_findings: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    xai_explanation: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    uncertainty: List[str] = field(default_factory=list)
    status: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProductAssessment:
    product_name: Optional[str]
    ingredients: List[Dict[str, Any]]
    overall_status: str
    overall_score: Optional[float]
    ingredient_assessments: List[IngredientAssessment]
    compliance_findings: List[Dict[str, Any]]
    health_findings: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    explanations: List[Dict[str, Any]]
    confidence: Optional[float]
    uncertainty: List[str]
    recommendations: List[str]
    status_reason: str
    disclaimer: str = "Development assessment only; not medical advice or a verified legal conclusion."
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["ingredient_assessments"] = [item.to_dict() for item in self.ingredient_assessments]
        return result
