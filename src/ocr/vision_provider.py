"""Configurable Vision OCR API provider.

The provider performs a real HTTP request only when `extract` is called and
configured. Its endpoint/response contract is intentionally small and
replaceable: POST JSON containing a base64 image and receive `text`, optional
`confidence`, and optional `bbox`.
"""
import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .ocr_provider import OCRProviderError, OCRResult


class VisionAPIConfigurationError(OCRProviderError):
    """Raised when API credentials or endpoint configuration is absent."""


class VisionAPIRequestError(OCRProviderError):
    """Raised when a configured Vision API request fails or is malformed."""


class VisionAPIProvider:
    """Call a configured Vision OCR endpoint; no API is called on import."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None, api_key_env: str = "VISION_OCR_API_KEY", endpoint_env: str = "VISION_OCR_ENDPOINT", timeout: float = 30.0):
        self.api_key = api_key if api_key is not None else os.getenv(api_key_env)
        self.endpoint = endpoint if endpoint is not None else os.getenv(endpoint_env)
        self.timeout = timeout

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise VisionAPIConfigurationError("Vision API mode requires configuration via VISION_OCR_API_KEY")
        if not self.endpoint:
            raise VisionAPIConfigurationError("Vision API mode requires configuration via VISION_OCR_ENDPOINT")

    @staticmethod
    def _confidence(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        if value > 1.5:
            value /= 100.0
        return max(0.0, min(1.0, value))

    def extract(self, image_path: str) -> OCRResult:
        self._validate_configuration()
        path = Path(image_path)
        if not path.is_file():
            raise VisionAPIRequestError(f"Image not found: {image_path}")
        try:
            payload = json.dumps({"image_base64": base64.b64encode(path.read_bytes()).decode("ascii")}).encode("utf-8")
            request = Request(self.endpoint, data=payload, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
            raise VisionAPIRequestError("Vision API request failed") from exc
        except Exception as exc:
            raise VisionAPIRequestError("Vision API request failed") from exc

        if not isinstance(body, dict) or not isinstance(body.get("text"), str):
            raise VisionAPIRequestError("Vision API returned an invalid OCR response")
        return OCRResult(
            text=body["text"],
            confidence=self._confidence(body.get("confidence")),
            bbox=body.get("bbox"),
            source="vision_api",
            metadata={key: value for key, value in body.items() if key not in {"text", "confidence", "bbox"}},
        )


__all__ = ["VisionAPIProvider", "VisionAPIConfigurationError", "VisionAPIRequestError"]
