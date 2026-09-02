"""Tests for the structured local regulatory evidence layer."""
from src.regulatory import (
    EvidenceStore,
    EvidenceStoreError,
    RegulatoryEvidence,
    add_evidence,
    get_evidence,
    list_evidence,
    load_demo_evidence,
    match_ingredient,
    remove_evidence,
    search_evidence,
)
from src.pipeline import PipelineConfig, run_product_pipeline


def _record(**overrides):
    values = {
        "ingredient": "citric acid", "ingredient_aliases": ["citric acid", "E330"],
        "source_title": "TEST DATA Document", "source_type": "demo", "authority": "TEST AUTHORITY",
        "document_id": "TEST-001", "section": "TEST SECTION", "page": 2,
        "text": "TEST DATA ONLY: citric acid example.", "jurisdiction": "TEST",
        "effective_date": None, "source_url": None, "evidence_type": "general_information",
        "confidence": 0.8, "notes": "DEMO DATA ONLY",
    }
    values.update(overrides)
    return RegulatoryEvidence(**values)


def _run_tests():
    store = EvidenceStore()
    added = add_evidence(store, _record())
    assert added["evidence_id"]
    assert get_evidence(store, added["evidence_id"])["source_title"] == "TEST DATA Document"
    assert list_evidence(store)[0]["document_id"] == "TEST-001"

    assert match_ingredient(store, "Citric Acid")[0]["ingredient"] == "citric acid"
    assert match_ingredient(store, "E330")[0]["ingredient"] == "citric acid"
    search = search_evidence(store, "citric acid example", ingredient="citric acid")
    assert search["status"] == "evidence_found"
    result = search["evidence"][0]
    assert result["authority"] == "TEST AUTHORITY"
    assert result["page"] == 2
    assert result["evidence_type"] == "general_information"
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["source_url"] is None

    no_evidence = search_evidence(store, "unlisted ingredient", ingredient="unlisted ingredient")
    assert no_evidence == {"status": "insufficient_evidence", "evidence": [], "message": "No authoritative evidence available."}
    assert match_ingredient(store, "unknown ingredient") == []

    duplicate = EvidenceStore()
    duplicate.add_evidence(_record())
    try:
        duplicate.add_evidence(_record())
        raise AssertionError("duplicate evidence should fail")
    except EvidenceStoreError:
        pass
    try:
        add_evidence(store, _record(confidence=1.2))
        raise AssertionError("invalid confidence should fail")
    except ValueError:
        pass
    try:
        add_evidence(store, _record(source_type="fake_source"))
        raise AssertionError("invalid source should fail")
    except ValueError:
        pass
    assert remove_evidence(store, added["evidence_id"]) is True
    assert get_evidence(store, added["evidence_id"]) is None

    demo = load_demo_evidence()
    demo_result = match_ingredient(demo, "demo additive")[0]
    assert demo_result["source_type"] == "demo"
    assert demo_result["authority"] == "TEST AUTHORITY"
    assert "TEST DATA ONLY" in demo_result["text"]
    assert "FSSAI" not in demo_result["source_title"]

    pipeline = run_product_pipeline(
        ocr_text="Ingredients: demo additive, unknown ingredient",
        config=PipelineConfig(regulatory_evidence_enabled=True, xai_enabled=False),
        regulatory_evidence_store=demo,
    )
    assert len(pipeline["evidence"]) == 2
    assert pipeline["evidence"][0]["status"] == "evidence_found"
    assert pipeline["evidence"][0]["sources"][0]["document_id"] == "TEST-DOC-001"
    assert pipeline["evidence"][1]["status"] == "insufficient_evidence"

    no_store = run_product_pipeline(ocr_text="Ingredients: sugar", config=PipelineConfig(regulatory_evidence_enabled=True, xai_enabled=False))
    assert any(error["stage"] == "regulatory_evidence" for error in no_store["errors"])
    assert not any("violation" in entry.get("message", "").lower() for entry in pipeline["evidence"])

    print("All regulatory evidence tests passed.")


if __name__ == "__main__":
    _run_tests()
