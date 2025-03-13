import cv2
import easyocr
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def processImageText(image_path):
    """
    Process the image to extract text using OCR and apply formatting.

    Args:
        image_path (str): Path to the image file.

    Returns:
        str: Formatted text extracted from the image.
    """
    try:
        # Step 1: Read the image using OpenCV
        logger.info("Reading image from path: %s", image_path)
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found at {image_path}")

        # Step 2: Initialize the EasyOCR reader
        logger.info("Initializing EasyOCR reader...")
        text_reader = easyocr.Reader(['en'])
        results = text_reader.readtext(img)

        # Step 3: Extract text from OCR results
        logger.info("Extracting text from OCR results...")
        extracted_texts = [text for (_, text, _) in results]
        receipt_text = ' '.join(extracted_texts)  # Join the text into a single string
        logger.info("Extracted OCR text: %s", receipt_text)

        # Step 4: Normalize the extracted text
        logger.info("Normalizing the extracted text...")
        #formatted_text = normalize_text(receipt_text)

        # Step 5: Format the text using regex patterns
        logger.info("Applying regex patterns to format the text...")
        formatted_text = apply_formatting_patterns(receipt_text)
        print('***************formatted_text********',formatted_text)

        # Step 6: Return the final formatted text
        logger.info("Text formatting complete.")
        return formatted_text.strip()

    except Exception as e:
        logger.error("Error processing image text: %s", str(e))
        raise


def normalize_text(receipt_text):
    """
    Normalize the extracted text by removing unnecessary spaces and formatting.

    Args:
        receipt_text (str): Original extracted text.

    Returns:
        str: Normalized text.
    """
    # Normalize spaces, commas, and other formatting issues
    receipt_text = re.sub(r'\s*,', r',', receipt_text)  # Remove space before commas
    receipt_text = re.sub(r',\s*', r',', receipt_text)  # Ensure no trailing space after commas
    receipt_text = re.sub(r'\s+', ' ', receipt_text)  # Replace multiple spaces with a single space
    receipt_text = re.sub(r'\s*,,', r',', receipt_text)  # Handle double commas
    return receipt_text


def apply_formatting_patterns(receipt_text):
    """
    Apply regex patterns to format specific sections of the text.

    Args:
        formatted_text (str): Text to be formatted.

    Returns:
        str: Formatted text.
    """
    receipt_text = re.sub(r'\s*,', r',', receipt_text)  # Remove space before commas
    receipt_text = re.sub(r',\s*', r',', receipt_text)  # Ensure no trailing space after commas
    receipt_text = re.sub(r'\s+', ' ', receipt_text)  # Replace multiple spaces with a single space
    receipt_text = re.sub(r'\s*,,', r',', receipt_text)  # Handle double commas
    formatted_text = ""
    # Add newlines before/after specific keywords or patterns
    formatted_text += re.sub(r'Kaufland', r'\nKaufland', receipt_text)  # New line before "Kaufland"
    formatted_text = re.sub(r'( \d{5} \w+)', r'\n\1', formatted_text)  # Address after zip code
    formatted_text = re.sub(r'(Tel \d{3}/\d{7})', r'\n\1', formatted_text)  # New line before telephone number
    formatted_text = re.sub(r'(Preis EUR)', r'\n\1\n', formatted_text)  # New line before price

    # Handle "K Card Rabatt" patterns
    formatted_text = re.sub(r'(K Card Rabatt)\s*([+-]?\d+[\s,.]\d{2})', r'\1 \2\n', formatted_text)

    # Normalize additional item lines
    normalized_text = re.sub(r'[_]', '', formatted_text)
    normalized_text_1 = re.sub(r'(\d+),\s+(\d+)', r'\1,\2', normalized_text)
    formatted_text = re.sub(r'([+-]?\d+[\s,.]\d{2})(?=\s+[A-B])\s+([A-B])', r'\1 \2\n', normalized_text_1)
    formatted_text = re.sub(r'(\d+,\d+)\s+([A-D])', r'\1 \2\n', formatted_text)  # New line before each item

    # Add newlines for totals, refunds, and tax details
    formatted_text = re.sub(r'Summe (\d+,\d+)', r'\nSumme \1', formatted_text)  # New line before the total
    formatted_text = re.sub(r'Summe (\d+) (\d{2})', r'\nSumme \1', formatted_text)

    formatted_text = re.sub(r'(Ruckgeld \d+,\d+)', r'\n\1', formatted_text)  # New line before refund
    formatted_text = re.sub(r'(Steuer %)', r'\n\1', formatted_text)  # New line before tax details

    # Format dates and times
    #formatted_text = re.sub(r'(Datum:?\s*\d{2}\.\d{2}\.\d{2})', r'\n\1', formatted_text)
    #formatted_text = re.sub(r'(Zeit:\s*\d{2}:\s*\d{2}:\s*\d{2})', r'\n\1', formatted_text)  # New line before time
    formatted_text = re.sub(r'(Datum:\s*\d{2}\s*\.\s*\d{2}\s*\.\s*\d{2})', r'\n\1', formatted_text)  # 12122024
    formatted_text = re.sub(r'(Datum:\s*\d{2}\.\d{2}\.\d{2})', r'\n\1', formatted_text)
    formatted_text = re.sub(r'(Datum:\s*\d{2}\.\d{2}\.\d{2})(?![\s\S]*Datum:)', r'\n\1', formatted_text)
    formatted_text = re.sub(r'(Datum:\s*\d{2}\.\d{2}\.\d{2})', r'\n\1', formatted_text)
    formatted_text = re.sub(r'(Datum \d{2} \d{2}\.\d{2})', r'\n\1', formatted_text)
    r'Datum (\d{2} \d{2}\.\d{2})'
    # Format additional metadata
    formatted_text = re.sub(r'(Bon:\s*\d+)', r'\n\1', formatted_text)  # New line before receipt number
    formatted_text = re.sub(r'(Filiale:\s*\d+)', r'\n\1', formatted_text)  # New line before branch number
    formatted_text = re.sub(r'(Kasse:\s*\d+)', r'\n\1', formatted_text)  # New line before checkout number
    formatted_text = re.sub(r'(Pay)', r'\n\1', formatted_text)  # New line before payment

    return formatted_text

