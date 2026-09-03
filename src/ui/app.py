"""Streamlit dashboard for the existing SIH-Compliance-AI backend."""
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List

try:
    import streamlit as st
except ImportError:  # pragma: no cover - exercised only before optional UI install
    st = None

from src.ocr import OCRProviderError, VisionAPIConfigurationError
from src.service import AnalysisService, AnalysisServiceError
from src.trace import build_trace, format_trace


def field_rows(label_result: Any) -> List[Dict[str, Any]]:
    """Convert label extraction output into displayable rows."""
    fields = label_result.to_dict().get("fields", {}) if hasattr(label_result, "to_dict") else (label_result or {}).get("fields", {})
    return [
        {"field": name, "value": field["value"], "confidence": field["confidence"], "method": field["method"], "source_text": field["source_text"]}
        for name, field in fields.items() if field
    ]


def build_analysis_state(ocr_result: Any, pipeline_report: Dict[str, Any], decision: Dict[str, Any], label_result: Any, trace: Any) -> Dict[str, Any]:
    """Build a UI state dictionary without changing backend result objects."""
    return {
        "ocr": ocr_result.__dict__ if hasattr(ocr_result, "__dict__") else ocr_result,
        "pipeline": pipeline_report,
        "decision": decision,
        "label": label_result.to_dict() if hasattr(label_result, "to_dict") else label_result,
        "trace": trace.to_dict() if hasattr(trace, "to_dict") else trace,
    }


def analyze_uploaded_image(uploaded_file: Any, mode: str, confidence_threshold: float) -> Dict[str, Any]:
    """Run the unified AnalysisService on a temporary uploaded image."""
    suffix = Path(uploaded_file.name or "label.png").suffix or ".png"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name
        result = AnalysisService().analyze_image(
            temp_path,
            ocr_mode=mode,
            product_data={"product_name": uploaded_file.name},
            confidence_threshold=confidence_threshold,
        )
        result_data = result.to_dict()
        return {
            "ocr": result_data["ocr_result"],
            "pipeline": result_data["pipeline_result"],
            "decision": result_data["decision"],
            "label": result_data["label_fields"],
            "trace": result_data["trace"],
            "analysis_result": result_data,
        }
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def _show_overview(state: Dict[str, Any]) -> None:
    decision = state["decision"]
    pipeline = state["pipeline"]
    st.subheader("Decision Overview")
    cols = st.columns(4)
    cols[0].metric("Final decision", decision.get("overall_status", "UNKNOWN"))
    cols[1].metric("Ingredients", decision.get("ingredient_assessments", []).__len__())
    cols[2].metric("Findings", len(decision.get("compliance_findings", [])))
    cols[3].metric("OCR confidence", state["ocr"].get("confidence") if state["ocr"].get("confidence") is not None else "n/a")
    st.write(decision.get("status_reason", ""))
    for warning in pipeline.get("errors", []):
        st.warning(f"{warning.get('stage', 'pipeline')}: {warning.get('message', 'Unknown issue')}")
    if decision.get("uncertainty"):
        st.info("Uncertainty: " + "; ".join(decision["uncertainty"]))


def _render_results(state: Dict[str, Any]) -> None:
    decision = state["decision"]
    pipeline = state["pipeline"]
    tabs = st.tabs(["Overview", "Ingredients", "Label Fields", "Compliance", "Evidence / RAG", "Why?", "Traceability"])
    with tabs[0]:
        _show_overview(state)
    with tabs[1]:
        rows = [{"original": item.get("ingredient"), "normalized": item.get("normalized_name"), "code": item.get("additive_code"), "status": item.get("status"), "findings": len(item.get("rule_results", []))} for item in decision.get("ingredient_assessments", [])]
        st.dataframe(rows, use_container_width=True)
    with tabs[2]:
        st.dataframe(field_rows(state["label"]), use_container_width=True)
    with tabs[3]:
        st.json(decision.get("compliance_findings", []))
    with tabs[4]:
        evidence = decision.get("evidence", [])
        if evidence:
            st.json(evidence)
        else:
            st.info("No evidence is available in the current analysis.")
    with tabs[5]:
        explanations = decision.get("explanations", [])
        if explanations:
            for explanation in explanations:
                st.write(explanation.get("consumer_explanation", explanation.get("technical_reason", "")))
                st.json(explanation)
        else:
            st.info("No XAI explanation is available.")
    with tabs[6]:
        trace_data = state.get("trace", {})
        if trace_data:
            st.text(format_trace(build_trace(pipeline, decision)))
            st.json({"nodes": trace_data.get("nodes", []), "edges": trace_data.get("edges", [])})
        else:
            st.info("No trace information is available.")
    with st.expander("Raw Analysis Data"):
        st.json(state)


def main() -> None:
    if st is None:
        raise RuntimeError("Streamlit is not installed. Run: pip install -r requirements.txt")
    st.set_page_config(page_title="SIH-Compliance-AI", page_icon="🔎", layout="wide")
    st.title("SIH-Compliance-AI")
    st.caption("AI-assisted food label compliance analysis with evidence-backed decisions.")
    uploaded_file = st.file_uploader("Upload a food-label image", type=["png", "jpg", "jpeg"])
    mode_label = st.selectbox("OCR mode", ["Local", "Vision API", "Auto"])
    mode = mode_label.casefold().replace(" ", "_")
    mode = {"local": "local", "vision_api": "api", "auto": "auto"}[mode]
    confidence_threshold = st.slider("Auto fallback confidence threshold", 0.0, 1.0, 0.70, 0.05)
    if uploaded_file:
        st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
        st.caption(f"File: {uploaded_file.name} | Size: {len(uploaded_file.getvalue()):,} bytes")
    if mode == "api" and (not os.getenv("VISION_OCR_API_KEY") or not os.getenv("VISION_OCR_ENDPOINT")):
        st.info("Vision API mode requires VISION_OCR_API_KEY and VISION_OCR_ENDPOINT.")
    if st.button("Analyze", type="primary", disabled=uploaded_file is None):
        try:
            with st.spinner("Analyzing label..."):
                state = analyze_uploaded_image(uploaded_file, mode, confidence_threshold)
            st.session_state["analysis_state"] = state
        except VisionAPIConfigurationError:
            st.error("Vision API is not configured. Choose Local mode or configure both Vision API environment variables.")
        except OCRProviderError:
            st.error("OCR could not process this image. Check the file and selected OCR mode.")
        except Exception:
            st.error("The analysis could not be completed. Check the image and try again.")
    if st.session_state.get("analysis_state"):
        _render_results(st.session_state["analysis_state"])


if __name__ == "__main__":
    main()
