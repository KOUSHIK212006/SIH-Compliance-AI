# OCR Providers

The OCR layer supports three modes through `OCRManager`:

- `local`: uses the existing CPU-compatible EasyOCR implementation in `ocr_engine.py`.
- `api`: calls a configured Vision OCR endpoint only when extraction is requested.
- `auto`: tries local OCR first and falls back to the API only when a quality
    check finds empty or short text, low confidence, too few useful tokens, or
    obvious OCR noise.

Quality thresholds are configurable without changing code:

- `OCR_MIN_CONFIDENCE` (default `0.70`)
- `OCR_MIN_USEFUL_TOKENS` (default `2`)
- `OCR_MIN_TEXT_LENGTH` (default `10`)

Each managed result includes the selected provider, local confidence, fallback
status and reason, final provider, and `ocr_duration_ms`. Image analysis adds
`analysis_duration_ms` when it runs through the managed OCR path.

API mode is optional. Configure it without putting secrets in source files:

```powershell
$env:VISION_OCR_API_KEY = "your-key"
$env:VISION_OCR_ENDPOINT = "https://your-vision-endpoint.example/ocr"
```

The configurable endpoint receives JSON containing `image_base64` and should
return JSON containing `text`, with optional `confidence` and `bbox`. The
provider is deliberately replaceable because Vision vendors use different
request formats. Missing API configuration in auto mode returns the local
result and records fallback metadata instead of failing.
