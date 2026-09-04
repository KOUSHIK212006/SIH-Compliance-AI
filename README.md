# SIH Compliance AI

AI-powered regulatory compliance inspection system for packaged food products.

## Goal

Automatically analyze product packaging using computer vision and OCR, extract regulatory information, and verify compliance against the latest applicable regulations.

## Planned Components

- Computer Vision
- OCR
- Regulatory RAG
- LLM-based compliance reasoning
- Ingredient analysis
- Confidence scoring
- Human-in-the-loop verification
- Regulatory version tracking
- Compliance dashboard

## Tech Stack

- Python
- FastAPI
- OpenCV
- YOLO
- OCR
- RAG / LLM
- React / TypeScript
- Firebase

## OCR Modes

- **LOCAL MODE**: Fully local EasyOCR processing. No API key is required, so
	it is suitable for offline and demo environments.
- **AUTO MODE**: Runs local OCR first and uses the Vision API only when local
	OCR quality is insufficient. This reduces API usage and cost.
- **API MODE**: Explicitly uses the configured Vision OCR API.

Auto-mode quality thresholds can be configured with `OCR_MIN_CONFIDENCE`,
`OCR_MIN_USEFUL_TOKENS`, and `OCR_MIN_TEXT_LENGTH`.

## Quick Demo

Run the complete image-to-trace analysis locally:

```powershell
python -m scripts.run_demo path/to/image.png
```

The demo uses **LOCAL** mode by default and runs the canonical
`AnalysisService` path through OCR, label extraction, ingredients, compliance,
evidence, decision, XAI, and traceability. Use `--ocr-mode auto` to enable
selective Vision API fallback, or `--ocr-mode api` to explicitly use Vision
OCR. LOCAL and AUTO are preferred for normal operation because they keep the
deterministic pipeline local and reduce external API usage; API mode requires
both Vision API environment variables.