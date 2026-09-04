"""Run and display one complete local-first SIH compliance analysis."""
import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from src.service import AnalysisService, AnalysisServiceError


def validate_image_path(image_path: str) -> Path:
    """Validate and normalize a demo image path before invoking the service."""
    path = Path(image_path).expanduser()
    if not path.is_file():
        raise ValueError(f"Image path does not exist or is not a file: {image_path}")
    return path


def _trace_is_valid(trace: Dict[str, Any]) -> bool:
    nodes = trace.get("nodes", [])
    edges = trace.get("edges", [])
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    return bool(trace.get("trace_id")) and len(node_ids) == len(nodes) and all(
        isinstance(edge, dict)
        and edge.get("source_id") in node_ids
        and edge.get("target_id") in node_ids
        for edge in edges
    )


def format_analysis_report(result: Any) -> str:
    """Format useful AnalysisResult data for a concise live demonstration."""
    ocr = result.ocr_result
    metadata = ocr.get("metadata", {})
    decision = result.decision
    trace = result.trace
    fields = result.label_fields.get("fields", {})
    recommendation = decision.get("recommendation") or decision.get("status_reason", "")
    explanation = result.explanations[0] if result.explanations else {}
    explanation_text = explanation.get("consumer_explanation") or explanation.get("technical_reason", "None")
    return "\n".join([
        "=" * 50,
        "SIH COMPLIANCE AI - END TO END ANALYSIS",
        "=" * 50,
        "",
        "OCR",
        f"Provider: {metadata.get('final_ocr_provider', ocr.get('source', 'unknown'))}",
        f"Confidence: {ocr.get('confidence') if ocr.get('confidence') is not None else 'n/a'}",
        f"Text length: {len(result.ocr_text)}",
        f"OCR duration: {metadata.get('ocr_duration_ms', 'n/a')} ms",
        "",
        "PRODUCT",
        f"Name: {result.product.get('product_name', 'Unknown product')}",
        "",
        "LABEL",
        f"Fields extracted: {len([field for field in fields.values() if field])}",
        "",
        "INGREDIENTS",
        f"Detected: {len(result.ingredients)}",
        f"Normalized: {len(result.normalized_ingredients)}",
        "",
        "COMPLIANCE",
        f"Findings: {len(result.compliance_findings)}",
        "",
        "EVIDENCE",
        f"Records: {len(result.evidence)}",
        "",
        "DECISION",
        f"Status: {decision.get('overall_status', 'unknown')}",
        f"Recommendation: {recommendation or 'n/a'}",
        "",
        "EXPLANATION",
        explanation_text,
        "",
        "TRACE",
        f"Nodes: {len(trace.get('nodes', []))}",
        f"Edges: {len(trace.get('edges', []))}",
        f"Valid: {_trace_is_valid(trace)}",
        f"Total analysis duration: {metadata.get('analysis_duration_ms', 'n/a')} ms",
        "",
        "=" * 50,
    ])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a complete SIH-Compliance-AI image analysis.")
    parser.add_argument("image_path", help="Path to an image file")
    parser.add_argument("--ocr-mode", choices=("local", "auto", "api"), default="local")
    args = parser.parse_args(argv)
    try:
        image_path = validate_image_path(args.image_path)
        result = AnalysisService().analyze_image(
            str(image_path),
            ocr_mode=args.ocr_mode,
            product_data={"product_name": image_path.name},
        )
    except (ValueError, AnalysisServiceError) as exc:
        print(f"Demo failed: {exc}", file=sys.stderr)
        return 2
    print(format_analysis_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())