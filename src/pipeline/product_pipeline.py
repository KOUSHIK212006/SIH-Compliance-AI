"""End-to-end orchestration of the existing SIH analysis modules."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.analysis import analyze_ingredient
from src.compliance import evaluate_ingredients
from src.ingredients import extract_ingredient_section, normalize_ingredient, parse_ingredients
from src.rag import retrieve_ingredient_evidence
from src.xai import explain_ingredient_analysis


@dataclass
class PipelineConfig:
    """Runtime options for the pipeline; defaults remain CPU-only and local."""

    ocr_languages: Optional[List[str]] = None
    ocr_gpu: bool = False
    ocr_confidence_threshold: float = 0.0
    rag_enabled: bool = False
    rag_top_k: int = 5
    xai_enabled: bool = True


def _error(stage: str, message: str) -> Dict[str, str]:
    return {"stage": stage, "message": message}


def _ocr_result(image_path: str, config: PipelineConfig, reader: Any = None) -> Dict[str, Any]:
    from src.ocr import ocr_engine

    return ocr_engine.ocr_image_path(
        image_path,
        langs=config.ocr_languages,
        reader=reader,
        gpu=config.ocr_gpu,
    )


def _empty_report(product: Dict[str, Any], ocr: Dict[str, Any], errors: List[Dict[str, str]], status: str, section: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    section = section or {"found": False, "raw_text": "", "confidence": 0.0, "warnings": []}
    return {
        "status": status,
        "product": product,
        "ocr": ocr,
        "ingredients": {"section_found": section.get("found", False), "section_text": section.get("raw_text", ""), "section_confidence": section.get("confidence", 0.0), "section": section, "raw": [], "normalized": [], "details": []},
        "analysis": {"overall_status": "not_available", "ingredient_results": []},
        "compliance": {"status": "not_available", "violations": [], "warnings": [], "findings": [], "errors": []},
        "evidence": [],
        "explanations": [],
        "summary": {"total_ingredients": 0, "known": 0, "unknown": 0, "requires_review": True},
        "errors": errors,
    }


def run_product_pipeline(
    image_path: Optional[str] = None,
    ocr_text: Optional[str] = None,
    *,
    product_data: Optional[Dict[str, Any]] = None,
    config: Optional[PipelineConfig] = None,
    rules: Optional[List[Dict[str, Any]]] = None,
    vector_store: Any = None,
    reader: Any = None,
) -> Dict[str, Any]:
    """Run the existing OCR-to-report pipeline from an image or OCR text.

    Exactly one of ``image_path`` or ``ocr_text`` should be supplied. RAG is
    attempted only when enabled and a vector store is supplied. Every failed
    optional stage is represented in ``errors`` rather than silently ignored.
    """
    config = config or PipelineConfig()
    product = dict(product_data or {})
    errors: List[Dict[str, str]] = []
    if (image_path is None) == (ocr_text is None):
        return _empty_report(product, {}, [_error("input", "provide exactly one of image_path or ocr_text")], "invalid_input")

    ocr: Dict[str, Any]
    if ocr_text is not None:
        if not isinstance(ocr_text, str):
            return _empty_report(product, {}, [_error("ocr", "ocr_text must be a string")], "ocr_failed")
        ocr = {"text": ocr_text, "mean_confidence": None, "source": "provided_text"}
    else:
        try:
            ocr = _ocr_result(image_path, config, reader)
        except Exception as exc:
            return _empty_report(product, {}, [_error("ocr", str(exc))], "ocr_failed")

    ocr_text_value = ocr.get("text", "")
    if not isinstance(ocr_text_value, str) or not ocr_text_value.strip():
        return _empty_report(product, ocr, [_error("ocr", "OCR produced no text")], "empty_ocr_text")
    confidence = ocr.get("mean_confidence")
    if isinstance(confidence, (int, float)) and confidence < config.ocr_confidence_threshold:
        errors.append(_error("ocr", f"OCR confidence {confidence:.3f} is below threshold {config.ocr_confidence_threshold:.3f}"))

    section = extract_ingredient_section(ocr_text_value)
    if not section["found"]:
        return _empty_report(product, ocr, errors + [_error("parser", "ingredients section not found")], "no_ingredient_section", section)
    section_text = section["raw_text"]
    if not section_text:
        return _empty_report(product, ocr, errors + [_error("parser", "ingredient section is empty")], "empty_ingredient_list", section)

    try:
        parsed = parse_ingredients(section_text)
    except Exception as exc:
        return _empty_report(product, ocr, errors + [_error("parser", str(exc))], "parser_failed")

    raw_values = [item["name"] for item in parsed.get("ingredients", []) if isinstance(item, dict) and item.get("name")]
    raw_values.extend(value for value in parsed.get("additives", []) if value)
    if not raw_values:
        return _empty_report(product, ocr, errors + [_error("parser", "ingredient section is empty")], "empty_ingredient_list", section)

    normalized = []
    for raw in raw_values:
        try:
            normalized.append(normalize_ingredient(raw))
        except Exception as exc:
            errors.append(_error("normalizer", str(exc)))
    if not normalized:
        return _empty_report(product, ocr, errors + [_error("normalizer", "no ingredients could be normalized")], "normalization_failed", section)

    details = parsed.get("ingredients", [])
    try:
        compliance = evaluate_ingredients(normalized, rules=rules)
    except Exception as exc:
        compliance = {"status": "error", "findings": [], "passed_rules": [], "failed_rules": [], "review_required": True, "errors": [_error("rule_engine", str(exc))]}
        errors.append(_error("rule_engine", str(exc)))

    analysis_results = []
    evidence = []
    explanations = []
    for record in normalized:
        try:
            analysis = analyze_ingredient(record)
            if analysis is None:
                continue
            analysis_results.append(analysis)
            if config.rag_enabled:
                if vector_store is None:
                    errors.append(_error("rag", "RAG is enabled but no vector store was supplied"))
                else:
                    try:
                        retrieved = retrieve_ingredient_evidence(record["canonical_name"], vector_store, top_k=config.rag_top_k)
                        evidence.extend(result.to_dict() for result in retrieved)
                    except Exception as exc:
                        errors.append(_error("rag", str(exc)))
            if config.xai_enabled:
                try:
                    explanations.append(explain_ingredient_analysis(analysis, compliance, input_ingredient=record.get("raw")))
                except Exception as exc:
                    errors.append(_error("xai", str(exc)))
        except Exception as exc:
            errors.append(_error("analyzer", str(exc)))

    known = sum(item.get("status") == "known" for item in analysis_results)
    unknown = len(analysis_results) - known
    requires_review = bool(errors) or bool(compliance.get("review_required")) or any(item.get("requires_review") for item in analysis_results)
    violations = [finding for finding in compliance.get("findings", []) if finding.get("severity") == "critical"]
    warnings = [finding for finding in compliance.get("findings", []) if finding.get("severity") != "critical"]
    return {
        "status": "review_required" if requires_review else "completed",
        "product": product,
        "ocr": {"text": ocr_text_value, "confidence": confidence, "details": ocr.get("details", []), "source": ocr.get("source", "image")},
        "ingredients": {"section_found": section["found"], "section_text": section["raw_text"], "section_confidence": section["confidence"], "section": section, "raw": raw_values, "normalized": normalized, "details": details},
        "analysis": {"overall_status": "review_required" if requires_review else "completed", "ingredient_results": analysis_results},
        "compliance": {"status": compliance.get("status"), "violations": violations, "warnings": warnings, "findings": compliance.get("findings", []), "errors": compliance.get("errors", [])},
        "evidence": evidence,
        "explanations": explanations,
        "summary": {"total_ingredients": len(raw_values), "known": known, "unknown": unknown, "requires_review": requires_review},
        "errors": errors,
    }


__all__ = ["PipelineConfig", "run_product_pipeline"]
