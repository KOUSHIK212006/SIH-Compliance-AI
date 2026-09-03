"""Build decision traces from existing pipeline and decision outputs."""
from typing import Any, Dict, List, Optional

from .models import DecisionTrace, TraceEdge, TraceNode, stable_id


def build_trace(pipeline_report: Dict[str, Any], decision: Optional[Dict[str, Any]] = None) -> DecisionTrace:
    """Adapt existing product outputs into a deterministic trace graph."""
    if not isinstance(pipeline_report, dict):
        raise TypeError("pipeline_report must be a dictionary")
    decision = decision or {}
    product = pipeline_report.get("product") if isinstance(pipeline_report.get("product"), dict) else {}
    product_name = str(product.get("product_name") or "Unknown product")
    nodes: List[TraceNode] = []
    edges: List[TraceEdge] = []
    warnings: List[str] = []

    def add(node: TraceNode) -> None:
        if node.id not in {item.id for item in nodes}:
            nodes.append(node)

    def link(source: Optional[TraceNode], target: Optional[TraceNode], relation: str) -> None:
        if source and target:
            edges.append(TraceEdge(source.id, target.id, relation))

    ocr = pipeline_report.get("ocr", {}) if isinstance(pipeline_report.get("ocr"), dict) else {}
    ocr_text = ocr.get("text", "")
    ocr_node = None
    if ocr_text:
        ocr_node = TraceNode(stable_id("ocr", {"text": ocr_text}), "OCR_TEXT", "OCR text", ocr_text, ocr.get("source"), ocr.get("confidence"), {"source": ocr.get("source", "unknown")})
        add(ocr_node)

    ingredients = pipeline_report.get("ingredients", {}) if isinstance(pipeline_report.get("ingredients"), dict) else {}
    section = ingredients.get("section") if isinstance(ingredients.get("section"), dict) else None
    if section and section.get("raw_text"):
        field_node = TraceNode(stable_id("label", {"name": "ingredients", "text": section["raw_text"]}), "LABEL_FIELD", "Ingredients field", section["raw_text"], "ingredient_section", section.get("confidence"), {"field": "ingredients"})
        add(field_node)
        link(ocr_node, field_node, "contains_label_field")
    else:
        field_node = None
        if ocr_node:
            warnings.append("ingredient label field metadata is unavailable")

    raw_values = ingredients.get("raw", []) if isinstance(ingredients.get("raw"), list) else []
    normalized = ingredients.get("normalized", []) if isinstance(ingredients.get("normalized"), list) else []
    analyses = pipeline_report.get("analysis", {}).get("ingredient_results", []) if isinstance(pipeline_report.get("analysis"), dict) else []
    findings = pipeline_report.get("compliance", {}).get("findings", []) if isinstance(pipeline_report.get("compliance"), dict) else []
    evidence = pipeline_report.get("evidence", []) if isinstance(pipeline_report.get("evidence"), list) else []
    explanations = pipeline_report.get("explanations", []) if isinstance(pipeline_report.get("explanations"), list) else []

    normalized_nodes = {}
    for index, record in enumerate(normalized):
        if not isinstance(record, dict) or not isinstance(record.get("canonical_name"), str):
            warnings.append(f"invalid normalized ingredient at index {index}")
            continue
        raw = record.get("raw", record["canonical_name"])
        ingredient_node = TraceNode(stable_id("ingredient", {"raw": raw, "index": index}), "INGREDIENT", str(raw), raw, "ingredient_parser", None, {"index": index})
        normalized_node = TraceNode(stable_id("normalized", {"name": record["canonical_name"], "index": index}), "NORMALIZED_INGREDIENT", record["canonical_name"], record["canonical_name"], "ingredient_normalizer", None, {"index": index, "additive_code": record.get("additive_code")})
        add(ingredient_node); add(normalized_node)
        link(field_node, ingredient_node, "extracts_ingredient")
        link(ingredient_node, normalized_node, "normalized_as")
        normalized_nodes[record["canonical_name"]] = normalized_node

        analysis = next((item for item in analyses if isinstance(item, dict) and item.get("canonical_name") == record["canonical_name"]), {})
        if analysis.get("category") or analysis.get("function"):
            knowledge_node = TraceNode(stable_id("knowledge", {"name": record["canonical_name"], "category": analysis.get("category"), "function": analysis.get("function")}), "KNOWLEDGE", record["canonical_name"], {"category": analysis.get("category"), "function": analysis.get("function")}, "ingredient_knowledge", analysis.get("confidence"), {})
            add(knowledge_node); link(normalized_node, knowledge_node, "described_by")

        for finding in findings:
            if not isinstance(finding, dict):
                continue
            target = str(finding.get("ingredient", ""))
            if target.casefold() not in {str(raw).casefold(), record["canonical_name"].casefold(), ""}:
                continue
            rule_node = TraceNode(stable_id("rule", finding), "RULE", str(finding.get("rule_id", "unknown rule")), finding, finding.get("source_type", "rule_engine"), None, {})
            add(rule_node); link(normalized_node, rule_node, "evaluated_by")
            for item in evidence:
                if isinstance(item, dict) and (item.get("ingredient", "").casefold() == record["canonical_name"].casefold() or item.get("status") == "evidence_found"):
                    evidence_node = TraceNode(stable_id("evidence", item), "EVIDENCE", str(item.get("message", "evidence")), item, "rag_or_regulatory_store", item.get("retrieval_score"), {})
                    add(evidence_node); link(rule_node, evidence_node, "supported_by")

    final = decision or {"overall_status": pipeline_report.get("status", "unknown")}
    decision_node = TraceNode(stable_id("decision", final), "DECISION", str(final.get("overall_status", final.get("status", "unknown"))), final, "decision_engine", final.get("confidence"), {})
    add(decision_node)
    for node in nodes:
        if node.type == "RULE":
            link(node, decision_node, "contributes_to")
    for explanation in explanations:
        if isinstance(explanation, dict):
            explanation_node = TraceNode(stable_id("explanation", explanation), "EXPLANATION", str(explanation.get("technical_reason", "explanation")), explanation, "xai", explanation.get("confidence"), {})
            add(explanation_node); link(decision_node, explanation_node, "explained_by")
    trace_id = stable_id("trace", {"product": product_name, "nodes": [node.to_dict() for node in nodes], "edges": [edge.to_dict() for edge in edges], "decision": final})
    trace = DecisionTrace(trace_id, product_name, nodes, edges, final, warnings)
    trace.warnings.extend(trace.validate())
    return trace
