"""Application service layer for product analysis requests."""
from pathlib import Path
import tempfile
from typing import Any, Dict, Optional

from src.decision import assess_product
from src.pipeline import run_product_pipeline


MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
_SIGNATURES = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".webp": b"RIFF",
    ".bmp": b"BM",
}


class APIServiceError(Exception):
    """Expected service-layer failure safe to expose to an API client."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def build_assessment(report: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an existing product-pipeline report into a ProductAssessment."""
    try:
        return assess_product(report)
    except Exception as exc:
        raise APIServiceError("Product assessment failed") from exc


def analyze_text(ingredient_text: str, product_name: Optional[str] = None, pipeline_runner: Any = run_product_pipeline) -> Dict[str, Any]:
    """Run the existing pipeline and decision engine for supplied text."""
    try:
        report = pipeline_runner(
            ocr_text=ingredient_text,
            product_data={"product_name": product_name} if product_name else {},
        )
        return build_assessment(report)
    except APIServiceError:
        raise
    except Exception as exc:
        raise APIServiceError("Text analysis failed") from exc


def _validate_upload(filename: Optional[str], content_type: Optional[str], content: bytes) -> str:
    suffix = Path(filename or "").suffix.casefold()
    if content_type not in ALLOWED_IMAGE_TYPES or suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise APIServiceError("Unsupported image type", 415)
    if not content:
        raise APIServiceError("Image upload is empty", 400)
    if len(content) > MAX_IMAGE_BYTES:
        raise APIServiceError("Image exceeds the 10 MB limit", 413)
    if not content.startswith(_SIGNATURES[suffix]):
        raise APIServiceError("Uploaded file content is not a valid image", 400)
    return suffix


async def analyze_image(upload: Any, product_name: Optional[str] = None, pipeline_runner: Any = run_product_pipeline) -> Dict[str, Any]:
    """Validate an upload, process it temporarily, and run existing modules."""
    content = await upload.read(MAX_IMAGE_BYTES + 1)
    suffix = _validate_upload(upload.filename, upload.content_type, content)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary.write(content)
            temporary_path = temporary.name
        report = pipeline_runner(
            image_path=temporary_path,
            product_data={"product_name": product_name} if product_name else {},
        )
        if report.get("status") == "ocr_failed":
            raise APIServiceError("Image OCR failed", 422)
        return build_assessment(report)
    except APIServiceError:
        raise
    except Exception as exc:
        raise APIServiceError("Image analysis failed") from exc
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)


__all__ = ["APIServiceError", "analyze_text", "analyze_image", "build_assessment"]
