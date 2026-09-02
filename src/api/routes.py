"""HTTP routes that delegate to the existing pipeline and decision engine."""
from pathlib import Path
import tempfile
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.decision import assess_product
from src.pipeline import run_product_pipeline

from .models import AnalyzeTextRequest, ProductAssessmentResponse


router = APIRouter()
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _assessment_from_pipeline(report: dict) -> dict:
    try:
        assessment = assess_product(report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Product assessment failed") from exc
    return ProductAssessmentResponse.model_validate(assessment).model_dump()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/analyze-text", response_model=ProductAssessmentResponse)
def analyze_text(request: AnalyzeTextRequest) -> dict:
    try:
        report = run_product_pipeline(
            ocr_text=request.ingredient_text,
            product_data={"product_name": request.product_name} if request.product_name else {},
        )
        return _assessment_from_pipeline(report)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Text analysis failed") from exc


@router.post("/analyze-image", response_model=ProductAssessmentResponse)
async def analyze_image(file: UploadFile = File(...), product_name: str | None = None) -> dict:
    suffix = Path(file.filename or "").suffix.casefold()
    if file.content_type not in ALLOWED_IMAGE_TYPES or suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    temporary_path = None
    try:
        content = await file.read(MAX_IMAGE_BYTES + 1)
        if not content:
            raise HTTPException(status_code=400, detail="Image upload is empty")
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image exceeds the 10 MB limit")

        # Validate image signature before handing the temporary path to OCR.
        signatures = {
            ".png": b"\x89PNG\r\n\x1a\n",
            ".jpg": b"\xff\xd8\xff",
            ".jpeg": b"\xff\xd8\xff",
            ".webp": b"RIFF",
            ".bmp": b"BM",
        }
        if not content.startswith(signatures[suffix]):
            raise HTTPException(status_code=400, detail="Uploaded file content is not a valid image")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary.write(content)
            temporary_path = temporary.name
        report = run_product_pipeline(
            image_path=temporary_path,
            product_data={"product_name": product_name} if product_name else {},
        )
        if report.get("status") == "ocr_failed":
            raise HTTPException(status_code=422, detail="Image OCR failed")
        return _assessment_from_pipeline(report)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Image analysis failed") from exc
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)


__all__ = ["router"]
