"""Pydantic request models for the FastAPI layer."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AnalyzeTextRequest(BaseModel):
    product_name: Optional[str] = Field(default=None, max_length=300)
    ingredient_text: str = Field(min_length=1, max_length=100_000)


class APIErrorResponse(BaseModel):
    detail: str
    error_type: str = "request_error"


class ProductAssessmentResponse(BaseModel):
    """Flexible response envelope for the existing structured assessment."""

    product_name: Optional[str] = None
    overall_status: str
    overall_score: Optional[float] = None
    ingredient_assessments: list[Dict[str, Any]]
    compliance_findings: list[Dict[str, Any]]
    health_findings: list[Dict[str, Any]]
    evidence: list[Dict[str, Any]]
    explanations: list[Dict[str, Any]]
    confidence: Optional[float] = None
    uncertainty: list[str]
    recommendations: list[str]
    status_reason: str
    disclaimer: str
    errors: list[Dict[str, Any]]
