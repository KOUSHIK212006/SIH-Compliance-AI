# Streamlit Demonstration UI

Install dependencies and start the dashboard:

```powershell
pip install -r requirements.txt
streamlit run src/ui/app.py
```

The dashboard uses the existing OCR manager, product pipeline, decision
engine, label extractor, and decision trace. Local OCR is the default and
requires no API key. Vision API mode is optional; configure it only when
needed:

```powershell
$env:VISION_OCR_API_KEY = "your-key"
$env:VISION_OCR_ENDPOINT = "https://your-vision-endpoint.example/ocr"
```

Auto mode tries local EasyOCR first and uses the existing manager fallback
policy. Uploaded images are held temporarily for processing and are not
stored permanently. No network call is made during application startup.
