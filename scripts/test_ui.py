"""Non-browser tests for the Streamlit demonstration interface."""
from types import SimpleNamespace

from src.label import extract_label_fields
from src.ui.app import build_analysis_state, field_rows


class DummyTrace:
    def to_dict(self):
        return {"trace_id": "trace:test", "nodes": [], "edges": []}


def _run_tests():
    assert build_analysis_state(
        SimpleNamespace(text="Ingredients: sugar", confidence=0.9),
        {"status": "completed"},
        {"overall_status": "REVIEW"},
        extract_label_fields("Ingredients: sugar"),
        DummyTrace(),
    )["trace"]["trace_id"] == "trace:test"

    rows = field_rows(extract_label_fields("Net Wt: 200 g\nIngredients: sugar"))
    assert any(row["field"] == "net_quantity" and row["value"] == "200 g" for row in rows)
    assert any(row["field"] == "ingredients" and row["source_text"] for row in rows)

    empty = {"fields": {}, "warnings": ["Ingredients field not found"]}
    assert field_rows(empty) == []
    state = build_analysis_state({}, {"errors": []}, {}, empty, {})
    assert state["label"] == empty
    assert state["trace"] == {}

    # Importing the app and calling helpers does not require API credentials.
    print("All UI tests passed.")


if __name__ == "__main__":
    _run_tests()
