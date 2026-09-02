"""Lightweight dataclasses for explainability and evidence results."""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceItem:
    """A traceable evidence or information item; no citation is invented."""

    source_id: str
    source_type: str
    title: str
    statement: str
    relevance: str
    evidence_strength: str
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReasoningStep:
    """One deterministic, auditable step in the explanation chain."""

    step: str
    description: str
    input: Any
    output: Any

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExplainableFinding:
    """Structured explanation of an existing analyzer/rule-engine result."""

    ingredient: str
    normalized_name: str
    category: Optional[str]
    function: Optional[str]
    status: str
    severity: Optional[str]
    confidence: Optional[float]
    technical_reason: str
    consumer_explanation: str
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    evidence: List[EvidenceItem] = field(default_factory=list)
    evidence_available: bool = False
    uncertainty: List[str] = field(default_factory=list)
    recommendation: str = "No recommendation is available from the current development data."
    disclaimer: str = "Development explanation only; not medical advice or a verified regulatory conclusion."
    rule_ids: List[str] = field(default_factory=list)
    knowledge_source_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["reasoning_steps"] = [step.to_dict() for step in self.reasoning_steps]
        result["evidence"] = [item.to_dict() for item in self.evidence]
        return result
