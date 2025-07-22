# shared/ReadImage.py

import cv2
import numpy as np
import easyocr
import os

# Initialize once globally
reader = easyocr.Reader(['de', 'en'])  # German and English

def processImageText(image_path):
    """
    Uses EasyOCR to extract text from the given image path.
    Returns the cleaned text as a single string.
    """
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Read the image using OpenCV
        image = cv2.imread(image_path)

        if image is None:
            raise ValueError(f"Failed to read image: {image_path}")

        # Convert image to grayscale (OCR works better)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Optional: apply thresholding or denoising here for better OCR

        # Use EasyOCR to extract text
        result = reader.readtext(gray, detail=0)  # detail=0 returns only text
        joined_text = "\n".join(result)

        return joined_text.strip()

    except Exception as e:
        print(f"[OCR Error] {e}")
        return ""
