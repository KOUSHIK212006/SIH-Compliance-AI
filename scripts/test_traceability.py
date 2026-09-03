"""Tests for deterministic Evidence Traceability / Decision Trace output."""
from src.decision import assess_product
from src.pipeline import run_product_pipeline
from src.trace import build_trace, format_decision_summary, format_trace


def _run_tests():
    report = run_product_pipeline(ocr_text="Product\nIngredients: sugar, sodium benzoate, unknown ingredient")
    decision = assess_product(report)
    trace = build_trace(report, decision)
    repeat = build_trace(report, decision)

    assert trace.validate() == []
    assert trace.to_dict() == repeat.to_dict()
    assert trace.to_json() == repeat.to_json()
    assert trace.trace_id == repeat.trace_id
    assert trace.get_nodes_by_type("OCR_TEXT")
    assert trace.get_nodes_by_type("LABEL_FIELD")
    assert len(trace.get_nodes_by_type("INGREDIENT")) == 3
    assert len(trace.get_nodes_by_type("NORMALIZED_INGREDIENT")) == 3
    assert trace.get_nodes_by_type("KNOWLEDGE")
    assert trace.get_nodes_by_type("RULE")
    assert trace.get_nodes_by_type("DECISION")
    assert trace.get_nodes_by_type("EXPLANATION")
    assert any(edge.relation == "normalized_as" for edge in trace.edges)
    assert any(edge.relation == "contributes_to" for edge in trace.edges)
    assert any(edge.relation == "explained_by" for edge in trace.edges)

    decision_node = trace.get_nodes_by_type("DECISION")[0]
    assert trace.get_upstream(decision_node.id)
    assert trace.get_downstream(decision_node.id)
    assert "DECISION:" in format_trace(trace)
    summary = format_decision_summary(trace)
    assert summary["trace_id"] == trace.trace_id

    incomplete = build_trace({"product": {}, "ocr": {"text": "x"}, "ingredients": {"normalized": []}}, {})
    assert incomplete.validate() == []
    assert incomplete.warnings
    assert b"image" not in incomplete.to_json().encode("utf-8")
    assert "image_bytes" not in incomplete.to_json()

    malformed = build_trace({"product": {}, "ingredients": {"normalized": [{"bad": True}]}}, {})
    assert malformed.validate() == []
    assert malformed.warnings

    print("All traceability tests passed.")


if __name__ == "__main__":
    _run_tests()
