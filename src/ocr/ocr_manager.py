"""Selection and fallback manager for local and Vision OCR providers."""
import os
import re
import time

from .local_provider import LocalOCRProvider
from .ocr_provider import OCRProviderError, OCRResult
from .vision_provider import VisionAPIProvider, VisionAPIConfigurationError


class OCRManager:
    """Select local, API, or automatic fallback OCR mode."""

    def __init__(self, mode: str = "local", local_provider=None, api_provider=None, confidence_threshold=None, min_tokens=None, min_text_length=None):
        if mode not in {"local", "api", "auto"}:
            raise ValueError("OCR mode must be one of: local, api, auto")
        confidence_threshold = self._env_float("OCR_MIN_CONFIDENCE", 0.70) if confidence_threshold is None else confidence_threshold
        min_tokens = self._env_int("OCR_MIN_USEFUL_TOKENS", 2) if min_tokens is None else min_tokens
        min_text_length = self._env_int("OCR_MIN_TEXT_LENGTH", 10) if min_text_length is None else min_text_length
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        if min_tokens < 0:
            raise ValueError("min_tokens must not be negative")
        if min_text_length < 0:
            raise ValueError("min_text_length must not be negative")
        self.mode = mode
        self.confidence_threshold = confidence_threshold
        self.min_tokens = min_tokens
        self.min_text_length = min_text_length
        self.local_provider = local_provider
        self.api_provider = api_provider
        if mode in {"local", "auto"} and self.local_provider is None:
            self.local_provider = LocalOCRProvider()
        if mode in {"api", "auto"} and self.api_provider is None:
            self.api_provider = VisionAPIProvider()

    @staticmethod
    def _env_float(name: str, default: float) -> float:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a number") from exc

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer") from exc

    def _quality_failure_reason(self, result: OCRResult):
        text = result.text.strip()
        if not text:
            return "empty_text"
        if len(text) < self.min_text_length:
            return "text_too_short"
        if result.confidence is not None and result.confidence < self.confidence_threshold:
            return "low_confidence"
        useful_tokens = re.findall(r"[A-Za-z0-9]{2,}", text)
        if len(useful_tokens) < self.min_tokens:
            return "too_few_useful_tokens"
        if not re.search(r"[A-Za-z]{2,}", text):
            return "ocr_noise"
        return None

    def _reliable(self, result: OCRResult) -> bool:
        return self._quality_failure_reason(result) is None

    def _finish(self, result: OCRResult, started: float, provider: str, *, fallback: bool, local_confidence=None, reason=None) -> OCRResult:
        result.metadata.update({
            "selected_provider": provider,
            "final_ocr_provider": provider,
            "fallback_occurred": fallback,
            "local_confidence": local_confidence if local_confidence is not None else result.confidence,
            "final_confidence": result.confidence,
            "ocr_duration_ms": round((time.perf_counter() - started) * 1000, 3),
        })
        if reason:
            result.metadata["fallback_reason"] = reason
        return result

    def extract(self, image_path: str) -> OCRResult:
        started = time.perf_counter()
        if self.mode == "local":
            return self._finish(self.local_provider.extract(image_path), started, "local_easyocr", fallback=False)
        if self.mode == "api":
            return self._finish(self.api_provider.extract(image_path), started, "vision_api", fallback=False)

        try:
            local = self.local_provider.extract(image_path)
        except OCRProviderError:
            local = OCRResult("", None, source="local_easyocr", metadata={"error": "local OCR failed"})
        reason = self._quality_failure_reason(local)
        if reason is None:
            return self._finish(local, started, "local_easyocr", fallback=False, local_confidence=local.confidence)
        try:
            api = self.api_provider.extract(image_path)
            return self._finish(api, started, "vision_api", fallback=True, local_confidence=local.confidence, reason=reason)
        except VisionAPIConfigurationError:
            local.metadata.update({"api_fallback_unavailable": True})
            return self._finish(local, started, "local_easyocr", fallback=False, local_confidence=local.confidence, reason=reason)


__all__ = ["OCRManager"]
