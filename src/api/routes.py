"""HTTP routes that delegate to the existing pipeline and decision engine."""
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.pipeline import run_product_pipeline

from .models import AnalyzeTextRequest, ProductAssessmentResponse
from .service import APIServiceError, analyze_image as service_analyze_image, analyze_text


router = APIRouter()
def _service_error(error: APIServiceError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=str(error))


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "SIH-Compliance-AI"}


@router.post("/analyze-text", response_model=ProductAssessmentResponse)
def analyze_text_route(request: AnalyzeTextRequest) -> dict:
    try:
        return analyze_text(request.ingredient_text, request.product_name, pipeline_runner=run_product_pipeline)
    except APIServiceError as exc:
        raise _service_error(exc) from exc


@router.post("/analyze", response_model=ProductAssessmentResponse)
async def analyze(file: UploadFile = File(...), product_name: Optional[str] = Form(default=None)) -> dict:
    try:
        return await service_analyze_image(file, product_name, pipeline_runner=run_product_pipeline)
    except APIServiceError as exc:
        raise _service_error(exc) from exc


@router.post("/analyze-image", response_model=ProductAssessmentResponse)
async def analyze_image(file: UploadFile = File(...), product_name: Optional[str] = Form(default=None)) -> dict:
    """Compatibility alias for the original image endpoint."""
    return await analyze(file, product_name)


__all__ = ["router"]
