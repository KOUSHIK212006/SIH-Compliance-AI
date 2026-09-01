"""Simple test script for the OCR module.

Creates a synthetic sample image with product-like text (if needed),
runs the OCR module on it, and prints results.
"""
import os
import sys
import numpy as np
import cv2

from src.ocr.ocr_engine import ocr_image_path, OCRException


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
        result = ocr_image_path(sample_path)
        print("--- OCR Extracted Text ---")
        print(result["text"] or "(no text found)")
        print("\nMean confidence:", result.get("mean_confidence"))
        print("\nDetails:")
        for det in result.get("details", []):
            print(det)

    except OCRException as e:
        print("OCR failed:", e)
        print("To install EasyOCR, run: pip install easyocr")
        sys.exit(2)


if __name__ == "__main__":
    main()
