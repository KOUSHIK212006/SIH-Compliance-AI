"""Behavior tests for the end-to-end product analysis orchestrator."""
from src.pipeline import PipelineConfig, run_product_pipeline
import src.pipeline.product_pipeline as pipeline_module


def _run_tests():
    report = run_product_pipeline(
        ocr_text="Ingredients: Sugar, Salt, Citric Acid (E330), Unknown Ingredient",
        product_data={"product_id": "test-product"},
    )
    assert report["status"] == "review_required"
    assert report["product"]["product_id"] == "test-product"
    assert report["ocr"]["text"].startswith("Ingredients:")
    # The existing parser returns named ingredients first and additive codes separately.
    assert report["ingredients"]["raw"] == ["Sugar", "Salt", "Citric Acid", "Unknown Ingredient", "E330"]
    assert [item["canonical_name"] for item in report["ingredients"]["normalized"]] == [
        "sugar", "salt", "citric acid", "unknown ingredient", "E330"
    ]
    assert len(report["analysis"]["ingredient_results"]) == 5
    assert report["summary"]["total_ingredients"] == 5
    assert report["summary"]["unknown"] == 1
    assert any(item["canonical_name"] == "unknown ingredient" for item in report["analysis"]["ingredient_results"])
    assert report["evidence"] == []
    assert report["explanations"]

    required_keys = {"product", "ocr", "ingredients", "analysis", "compliance", "evidence", "explanations", "summary", "errors"}
    assert required_keys.issubset(report)
    assert {"raw", "normalized", "details"}.issubset(report["ingredients"])
    assert {"overall_status", "ingredient_results"}.issubset(report["analysis"])
    assert {"status", "violations", "warnings", "findings", "errors"}.issubset(report["compliance"])

    no_rag = run_product_pipeline(ocr_text="Ingredients: Sugar", config=PipelineConfig(rag_enabled=False))
    assert no_rag["evidence"] == []
    assert not any(error["stage"] == "rag" for error in no_rag["errors"])

    no_xai = run_product_pipeline(ocr_text="Ingredients: Sugar", config=PipelineConfig(xai_enabled=False))
    assert no_xai["explanations"] == []
    assert no_xai["analysis"]["ingredient_results"]

    empty = run_product_pipeline(ocr_text="Ingredients:")
    assert empty["status"] == "empty_ingredient_list"
    assert empty["ingredients"]["raw"] == []
    assert empty["errors"]

    no_section = run_product_pipeline(ocr_text="Nutrition facts only")
    assert no_section["status"] == "no_ingredient_section"
    assert no_section["errors"][0]["stage"] == "parser"

    ocr_failure = run_product_pipeline(image_path="missing-product-image.png")
    assert ocr_failure["status"] == "ocr_failed"
    assert ocr_failure["errors"][0]["stage"] == "ocr"

    low_confidence = run_product_pipeline(
        ocr_text="Ingredients: Sugar",
        config=PipelineConfig(ocr_confidence_threshold=0.9),
    )
    assert low_confidence["ocr"]["confidence"] is None
    assert low_confidence["status"] == "completed"

    calls = {"parser": 0, "normalizer": 0}
    original_parser = pipeline_module.parse_ingredients
    original_normalizer = pipeline_module.normalize_ingredient

    def parser_probe(text):
        calls["parser"] += 1
        return original_parser(text)

    def normalizer_probe(value):
        calls["normalizer"] += 1
        return original_normalizer(value)

    pipeline_module.parse_ingredients = parser_probe
    pipeline_module.normalize_ingredient = normalizer_probe
    try:
        probed = run_product_pipeline(ocr_text="Ingredients: Sugar, Salt")
    finally:
        pipeline_module.parse_ingredients = original_parser
        pipeline_module.normalize_ingredient = original_normalizer
    assert probed["status"] == "completed"
    assert calls["parser"] == 1
    assert calls["normalizer"] == 2

    print("All product pipeline tests passed.")


if __name__ == "__main__":
    _run_tests()
