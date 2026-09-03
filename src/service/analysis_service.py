"""Unified orchestration service for product analysis."""
from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional

from src.decision import assess_product
from src.label import LabelFieldExtractor
from src.ocr import OCRManager, OCRProviderError, OCRResult
from src.pipeline import PipelineConfig, run_product_pipeline
from src.trace import build_trace

from .models import AnalysisResult


class AnalysisServiceError(Exception):
    """Controlled failure raised when a required analysis stage fails."""


class AnalysisService:
    """Coordinate existing modules without implementing their algorithms."""

    def __init__(
        self,
        ocr_manager_factory: Optional[Callable[..., OCRManager]] = None,
        pipeline_runner: Callable[..., Dict[str, Any]] = run_product_pipeline,
        decision_runner: Callable[[Dict[str, Any]], Dict[str, Any]] = assess_product,
        label_extractor: Optional[LabelFieldExtractor] = None,
        trace_builder: Callable[..., Any] = build_trace,
    ):
        self._ocr_manager_factory = ocr_manager_factory or OCRManager
        self._pipeline_runner = pipeline_runner
        self._decision_runner = decision_runner
        self._label_extractor = label_extractor or LabelFieldExtractor()
        self._trace_builder = trace_builder

    @staticmethod
    def _ocr_dict(result: OCRResult) -> Dict[str, Any]:
        return {
            "text": result.text,
            "confidence": result.confidence,
            "bbox": result.bbox,
            "source": result.source,
            "metadata": result.metadata,
        }

    def analyze_image(
        self,
        image_path: str,
        ocr_mode: str = "local",
        *,
        product_data: Optional[Dict[str, Any]] = None,
        pipeline_config: Optional[PipelineConfig] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        vector_store: Any = None,
        regulatory_evidence_store: Any = None,
        confidence_threshold: float = 0.70,
        min_tokens: int = 2,
    ) -> AnalysisResult:
        """Analyze an image through OCR and all existing downstream modules."""
        if not isinstance(image_path, str) or not image_path.strip():
            raise AnalysisServiceError("image_path must be a non-empty string")
        if ocr_mode not in {"local", "api", "auto"}:
            raise AnalysisServiceError("ocr_mode must be one of: local, api, auto")

        try:
            manager = self._ocr_manager_factory(
                mode=ocr_mode,
                confidence_threshold=confidence_threshold,
                min_tokens=min_tokens,
            )
            ocr_result = manager.extract(image_path)
        except OCRProviderError as exc:
            raise AnalysisServiceError(str(exc)) from exc
        except Exception as exc:
            raise AnalysisServiceError("OCR stage failed") from exc
        if not isinstance(ocr_result, OCRResult):
            raise AnalysisServiceError("OCR manager returned an invalid OCRResult")
        return self.analyze_ocr_result(
            ocr_result,
            product_data=product_data,
            pipeline_config=pipeline_config,
            rules=rules,
            vector_store=vector_store,
            regulatory_evidence_store=regulatory_evidence_store,
        )

    def analyze_ocr_result(
        self,
        ocr_result: OCRResult,
        *,
        product_data: Optional[Dict[str, Any]] = None,
        pipeline_config: Optional[PipelineConfig] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        vector_store: Any = None,
        regulatory_evidence_store: Any = None,
    ) -> AnalysisResult:
        """Continue analysis from an already obtained provider-neutral OCR result."""
        if not isinstance(ocr_result, OCRResult):
            raise AnalysisServiceError("ocr_result must be an OCRResult")
        if not ocr_result.text.strip():
            raise AnalysisServiceError("OCR returned no text")

        config = pipeline_config or PipelineConfig()
        config = replace(
            config,
            rag_enabled=config.rag_enabled and vector_store is not None,
            regulatory_evidence_enabled=config.regulatory_evidence_enabled and regulatory_evidence_store is not None,
        )
        warnings: List[str] = []
        if pipeline_config and pipeline_config.rag_enabled and vector_store is None:
            warnings.append("RAG was enabled but no vector store was supplied")
        if pipeline_config and pipeline_config.regulatory_evidence_enabled and regulatory_evidence_store is None:
            warnings.append("Regulatory evidence was enabled but no evidence store was supplied")

        try:
            pipeline_result = self._pipeline_runner(
                ocr_text=ocr_result.text,
                product_data=product_data or {},
                config=config,
                rules=rules,
                vector_store=vector_store,
                regulatory_evidence_store=regulatory_evidence_store,
            )
        except Exception as exc:
            raise AnalysisServiceError("Product pipeline stage failed") from exc

        try:
            label_result = self._label_extractor.extract(ocr_result.text)
            label_fields = label_result.to_dict()
        except Exception as exc:
            raise AnalysisServiceError("Label extraction stage failed") from exc

        try:
            decision = self._decision_runner(pipeline_result)
        except Exception as exc:
            raise AnalysisServiceError("Decision stage failed") from exc

        try:
            trace = self._trace_builder(pipeline_result, decision).to_dict()
        except Exception as exc:
            raise AnalysisServiceError("Traceability stage failed") from exc

        ingredients = pipeline_result.get("ingredients", {})
        compliance = pipeline_result.get("compliance", {})
        result = AnalysisResult(
            ocr_result=self._ocr_dict(ocr_result),
            ocr_text=ocr_result.text,
            product=dict(product_data or pipeline_result.get("product", {})),
            pipeline_result=pipeline_result,
            label_fields=label_fields,
            ingredients=ingredients.get("raw", []) if isinstance(ingredients, dict) else [],
            normalized_ingredients=ingredients.get("normalized", []) if isinstance(ingredients, dict) else [],
            compliance_findings=compliance.get("findings", []) if isinstance(compliance, dict) else [],
            evidence=pipeline_result.get("evidence", []),
            decision=decision,
            explanations=pipeline_result.get("explanations", []),
            trace=trace,
            warnings=warnings + list(label_result.warnings),
            errors=list(pipeline_result.get("errors", [])),
        )
        return result


def analyze_image(*args: Any, **kwargs: Any) -> AnalysisResult:
    """Convenience wrapper using a default ``AnalysisService`` instance."""
    return AnalysisService().analyze_image(*args, **kwargs)


__all__ = ["AnalysisService", "AnalysisServiceError", "analyze_image"]
