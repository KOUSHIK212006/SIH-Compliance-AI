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