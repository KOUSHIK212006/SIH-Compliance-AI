"""Tests for the unified AnalysisService orchestration layer."""
from pathlib import Path

from src.ocr import OCRResult, VisionAPIConfigurationError
from src.pipeline import PipelineConfig
from src.service import AnalysisService, AnalysisServiceError


class FakeOCRManager:
    def __init__(self, mode, confidence_threshold, min_tokens):
        self.mode = mode
        self.calls = []

    def extract(self, image_path):
        self.calls.append(image_path)
        return OCRResult("Ingredients: sugar, unknown ingredient", 0.88, source=f"fake_{self.mode}")


def fake_manager_factory(**kwargs):
    return FakeOCRManager(**kwargs)


def _run_tests():
    service = AnalysisService(ocr_manager_factory=fake_manager_factory)
    image_path = str(Path.cwd() / "sample_package.png")
    result = service.analyze_image(image_path, ocr_mode="local", product_data={"product_name": "Demo"})
    output = result.to_dict()
    assert isinstance(result.ocr_result, dict)
    assert output["ocr_text"].startswith("Ingredients:")
    assert output["product"]["product_name"] == "Demo"
    assert output["ingredients"] == ["sugar", "unknown ingredient"]
    assert [item["canonical_name"] for item in output["normalized_ingredients"]] == ["sugar", "unknown ingredient"]
    assert output["decision"]["overall_status"] == "REVIEW"
    assert output["trace"]["trace_id"]
    assert output["explanations"]
    assert output["label_fields"]["fields"]["ingredients"]["value"] == "sugar, unknown ingredient"

    api_result = service.analyze_image(image_path, ocr_mode="api")
    assert api_result.ocr_result["source"] == "fake_api"
    auto_result = service.analyze_image(image_path, ocr_mode="auto")
    assert auto_result.ocr_result["source"] == "fake_auto"

    disabled = service.analyze_image(image_path, pipeline_config=PipelineConfig(rag_enabled=False, xai_enabled=False))
    assert disabled.evidence == []
    assert disabled.explanations == []

    deterministic = service.analyze_image(image_path, product_data={"product_name": "Demo"})
    deterministic_again = service.analyze_image(image_path, product_data={"product_name": "Demo"})
    assert deterministic.to_dict() == deterministic_again.to_dict()
    assert "image_bytes" not in deterministic.to_json()

    try:
        service.analyze_image("", ocr_mode="local")
        raise AssertionError("empty image path should fail")
    except AnalysisServiceError:
        pass
    try:
        service.analyze_image(image_path, ocr_mode="invalid")
        raise AssertionError("invalid mode should fail")
    except AnalysisServiceError:
        pass
    try:
        service.analyze_ocr_result(OCRResult("", None, source="fake"))
        raise AssertionError("empty OCR should fail")
    except AnalysisServiceError:
        pass

    def failing_factory(**kwargs):
        raise VisionAPIConfigurationError("Vision API mode requires configuration")

    try:
        AnalysisService(ocr_manager_factory=failing_factory).analyze_image(image_path, ocr_mode="api")
        raise AssertionError("API configuration failure should propagate")
    except AnalysisServiceError as exc:
        assert "configuration" in str(exc).lower()

    print("All analysis service tests passed.")


if __name__ == "__main__":
    _run_tests()
