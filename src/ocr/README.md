# OCR Providers

The OCR layer supports three modes through `OCRManager`:

- `local`: uses the existing CPU-compatible EasyOCR implementation in `ocr_engine.py`.
- `api`: calls a configured Vision OCR endpoint only when extraction is requested.
- `auto`: tries local OCR first and falls back to the API when text is empty,
  confidence is below the configured threshold, or there are too few tokens.

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
