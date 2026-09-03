"""Data models for deterministic product decision traces."""
import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


NODE_TYPES = {"OCR_TEXT", "LABEL_FIELD", "INGREDIENT", "NORMALIZED_INGREDIENT", "KNOWLEDGE", "RULE", "EVIDENCE", "DECISION", "EXPLANATION"}


def stable_id(prefix: str, value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


@dataclass
class TraceNode:
    id: str
    type: str
    label: str
    value: Any = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.type not in NODE_TYPES:
            raise ValueError(f"unsupported trace node type: {self.type}")
        if self.confidence is not None:
            self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TraceEdge:
    source_id: str
    target_id: str
    relation: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class DecisionTrace:
    trace_id: str
    product_name: str
    nodes: List[TraceNode] = field(default_factory=list)
    edges: List[TraceEdge] = field(default_factory=list)
    final_decision: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "product_name": self.product_name,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "final_decision": self.final_decision,
            "warnings": self.warnings,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def get_nodes_by_type(self, node_type: str) -> List[TraceNode]:
        return [node for node in self.nodes if node.type == node_type]

    def get_upstream(self, node_id: str) -> List[TraceNode]:
        source_ids = {edge.source_id for edge in self.edges if edge.target_id == node_id}
        return [node for node in self.nodes if node.id in source_ids]

    def get_downstream(self, node_id: str) -> List[TraceNode]:
        target_ids = {edge.target_id for edge in self.edges if edge.source_id == node_id}
        return [node for node in self.nodes if node.id in target_ids]

    def validate(self) -> List[str]:
        errors = []
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("duplicate node IDs")
        known_ids = set(node_ids)
        for edge in self.edges:
            if edge.source_id not in known_ids or edge.target_id not in known_ids:
                errors.append("edge references an unknown node")
        if not self.trace_id:
            errors.append("trace_id is required")
        return errors
