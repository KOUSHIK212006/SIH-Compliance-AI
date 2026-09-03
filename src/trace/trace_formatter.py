"""Human-readable and machine-friendly trace formatting."""
from typing import Any, Dict

from .models import DecisionTrace


def format_trace(trace: DecisionTrace) -> str:
    """Render a concise graph-oriented explanation of a decision trace."""
    if not isinstance(trace, DecisionTrace):
        raise TypeError("trace must be a DecisionTrace")
    decision = trace.final_decision.get("overall_status", trace.final_decision.get("status", "UNKNOWN"))
    lines = [f"DECISION: {decision}", "", "Trace:"]
    for node_type in ("OCR_TEXT", "LABEL_FIELD", "INGREDIENT", "NORMALIZED_INGREDIENT", "KNOWLEDGE", "RULE", "EVIDENCE", "DECISION", "EXPLANATION"):
        nodes = trace.get_nodes_by_type(node_type)
        if nodes:
            lines.append(f"- {node_type}: " + ", ".join(node.label for node in nodes))
    if trace.warnings:
        lines.extend(["", "Warnings:"] + [f"- {warning}" for warning in trace.warnings])
    return "\n".join(lines)


def format_decision_summary(trace: DecisionTrace) -> Dict[str, Any]:
    """Return a UI-ready decision summary without adding conclusions."""
    return {
        "decision": trace.final_decision.get("overall_status", trace.final_decision.get("status", "UNKNOWN")),
        "reason": trace.final_decision.get("status_reason", "Decision supplied by the existing decision engine."),
        "trace_id": trace.trace_id,
        "warning_count": len(trace.warnings),
        "evidence_count": len(trace.get_nodes_by_type("EVIDENCE")),
        "rule_count": len(trace.get_nodes_by_type("RULE")),
    }


__all__ = ["format_trace", "format_decision_summary"]
