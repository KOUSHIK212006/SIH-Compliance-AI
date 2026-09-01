"""Simple test script for the OCR module.

Creates a synthetic sample image with product-like text (if needed),
runs the OCR module on it, and prints results.
"""
import os
import sys
import numpy as np
import cv2

from src.ocr.ocr_engine import ocr_image_path, OCRException, init_reader


def create_sample_image(path: str) -> None:
    img = 255 * np.ones((240, 800, 3), dtype=np.uint8)
    cv2.putText(img, "Test Product", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 3)
    cv2.putText(img, "Net wt 200g", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    cv2.imwrite(path, img)


def main():
    sample_path = os.path.join(os.getcwd(), "sample_package.png")

    if not os.path.exists(sample_path):
        print(f"Creating sample image at {sample_path}")
        create_sample_image(sample_path)

    try:
        # Initialize a reader once and pass it to the OCR call for reuse
        reader = init_reader(langs=["en"], gpu=False)
        result = ocr_image_path(sample_path, reader=reader, debug=False)
        print("--- OCR Extracted Text ---")
        print(result["text"] or "(no text found)")
        print("\nMean confidence:", result.get("mean_confidence"))
        print("\nDetails:")
        for det in result.get("details", []):
            print(det)

        # Basic assertions for smoke test
        assert "text" in result
        assert "details" in result and isinstance(result["details"], list)
        # there should be at least one detection for our sample image
        assert len(result["details"]) >= 1, "Expected at least one OCR detection"
        # mean confidence must be between 0 and 1 when present
        mc = result.get("mean_confidence")
        if mc is not None:
            assert 0.0 <= mc <= 1.0, f"mean_confidence out of range: {mc}"
        # each detection confidence normalized
        for d in result.get("details", []):
            c = d.get("confidence")
            assert c is not None and 0.0 <= c <= 1.0, f"detection confidence out of range: {c}"

        print("\nSmoke test assertions passed.")

    except OCRException as e:
        print("OCR failed:", e)
        print("To install EasyOCR, run: pip install easyocr")
        sys.exit(2)


if __name__ == "__main__":
    main()
