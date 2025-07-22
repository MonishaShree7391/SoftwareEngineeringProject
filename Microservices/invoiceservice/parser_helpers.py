# invoiceservice/shared/parser_helpers.py

from flask import current_app

from ReadPdf import pdf_to_jpg
from scanner import ImageScanner
from rewe import extract_text_from_pdf  # if REWE-specific logic
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



def create_dataframe(pdf_path, filename, month, year, shopname, userid):
    """
    Processes a PDF file, extracts data into a DataFrame, and associates it with a user ID.
    """
    try:
        # 1. Text-based (REWE)
        if shopname.lower() == 'rewe':
            print(f"[DEBUG] Using PDF path for REWE: {pdf_path}")
            extracted_text = extract_text_from_pdf(pdf_path)
            if extracted_text:
                print('text has been extracted')
            scanned_object = ImageScanner('', filename, extracted_text, month, year)
        else:
            # 2. Image-based (Kaufland, etc.)
            image_path = pdf_to_jpg(pdf_path, filename, current_app.config['IMAGE_FOLDER'])
            scanned_object = ImageScanner(image_path, filename, '', month, year)

        # 3. Extract text & grocery data
        text = scanned_object.get_text()
        scanned_object.get_groceries_bill()
        df = scanned_object.create_data_frame()

        if df.empty:
            raise ValueError("Failed to extract valid data from the PDF.")
        else:
            print('DATAFRAME CREATED')
        df['userid'] = userid
        print('DATAFRAME CREATED')
        return df

    except Exception as e:
        logger.error(f"Error creating DataFrame from PDF: {str(e)}")
        raise
