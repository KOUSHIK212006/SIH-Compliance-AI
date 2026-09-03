"""Tests for local, Vision API, and automatic OCR provider selection."""
import os
from pathlib import Path

from src.ocr import (
    LocalOCRProvider,
    OCRManager,
    OCRProviderError,
    OCRResult,
    VisionAPIConfigurationError,
    VisionAPIProvider,
)


class FakeProvider:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def extract(self, image_path):
        self.calls += 1
        return OCRResult(**self.result.__dict__)


def _run_tests():
    sample_path = str(Path.cwd() / "sample_package.png")
    local = LocalOCRProvider(languages=["en"], gpu=False)
    local_result = local.extract(sample_path)
    assert isinstance(local_result, OCRResult)
    assert local_result.source == "local_easyocr"
    assert local_result.text
    assert local_result.confidence is None or 0.0 <= local_result.confidence <= 1.0
    assert local_result.metadata["details"]

    manager_local = OCRManager(mode="local", local_provider=FakeProvider(local_result))
    managed_local = manager_local.extract(sample_path)
    assert managed_local.source == "local_easyocr"
    assert managed_local.metadata["details"]

    reliable = OCRResult("reliable local text", 0.95, source="local_easyocr")
    local_fake = FakeProvider(reliable)
    api_fake = FakeProvider(OCRResult("api text", 0.90, source="vision_api"))
    auto_reliable = OCRManager(mode="auto", local_provider=local_fake, api_provider=api_fake, confidence_threshold=0.7, min_tokens=2)
    result = auto_reliable.extract(sample_path)
    assert result.source == "local_easyocr"
    assert result.metadata["selected_provider"] == "local_easyocr"
    assert result.metadata["fallback_occurred"] is False
    assert api_fake.calls == 0

    weak_local = FakeProvider(OCRResult("x", 0.2, source="local_easyocr"))
    unavailable_api = VisionAPIProvider(api_key="", endpoint="")
    auto_fallback = OCRManager(mode="auto", local_provider=weak_local, api_provider=unavailable_api, confidence_threshold=0.7, min_tokens=2)
    fallback_result = auto_fallback.extract(sample_path)
    assert fallback_result.source == "local_easyocr"
    assert fallback_result.metadata["api_fallback_unavailable"] is True
    assert fallback_result.metadata["local_confidence"] == 0.2

    api = VisionAPIProvider(api_key=None, endpoint=None)
    old_key = os.environ.pop("VISION_OCR_API_KEY", None)
    old_endpoint = os.environ.pop("VISION_OCR_ENDPOINT", None)
    try:
        try:
            api.extract(sample_path)
            raise AssertionError("missing API configuration should fail")
        except VisionAPIConfigurationError:
            pass
    finally:
        if old_key is not None:
            os.environ["VISION_OCR_API_KEY"] = old_key
        if old_endpoint is not None:
            os.environ["VISION_OCR_ENDPOINT"] = old_endpoint

    try:
        OCRManager(mode="invalid")
        raise AssertionError("invalid mode should fail")
    except ValueError:
        pass
    try:
        OCRManager(mode="local", local_provider=FakeProvider(reliable), confidence_threshold=1.1)
        raise AssertionError("invalid threshold should fail")
    except ValueError:
        pass

    low = OCRManager(mode="auto", local_provider=FakeProvider(OCRResult("one", 0.95, source="local_easyocr")), api_provider=api_fake, min_tokens=2)
    low_result = low.extract(sample_path)
    assert low_result.metadata["fallback_occurred"] is True
    assert low_result.source == "vision_api"

    print("All vision OCR provider tests passed.")


if __name__ == "__main__":
    _run_tests()
