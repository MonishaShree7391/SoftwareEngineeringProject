import pandas as pd
from flask import current_app
from app.utils.ReadPdf import pdf_to_jpg
from app.services.groceries import ImageScanner
import logging
from sqlalchemy import inspect, text
import pandas as pd
from app.models.models import get_session
import re
from app.services.rewe  import extract_text_from_pdf
#import datetime
from datetime import datetime

logger = logging.getLogger(__name__)

def create_dataframe(pdf_path, filename, month,year, shopname,userid):
    """
    Processes a PDF file, extracts data into a DataFrame, and associates it with a user ID.
    """
    try:
        # Convert PDF to an image
        if shopname == 'rewe':
            extracted_text = extract_text_from_pdf(filename)
            scanned_object = ImageScanner('', filename, extracted_text, month, year)
        else:
            image_path = pdf_to_jpg(pdf_path, filename, current_app.config['IMAGE_FOLDER'])
            scanned_object = ImageScanner(image_path, filename, '', month, year)

        # Extract text from the image
        text = scanned_object.get_text()
        if not text or len(text) < 10:
            logger.warning("Insufficient text detected. Attempting secondary processing.")
            scanned_object.get_grocery_bill()
            df = scanned_object.create_data_frame()
        else:
            scanned_object.get_grocery_bill()
            df = scanned_object.create_data_frame()

        # Validate DataFrame
        if df.empty:
            logger.error("Extracted DataFrame is empty. No data found in the PDF.")
            raise ValueError("Failed to extract valid data from the PDF.")

        # Add the user ID to the DataFrame
        df['userid'] = userid
        pd.set_option("display.max_columns", None)

        # Log the result
        logger.info(f"DataFrame created successfully for user ID {userid}.")
        logger.debug(f"Extracted DataFrame:\n{df}")

        return df

    except Exception as e:
        logger.error(f"Error creating DataFrame from PDF: {str(e)}")
        raise

def convert_date(date_str):
    try:
        # Normalize the input by removing spaces around dots
        normalized_date = re.sub(r'\s*\.\s*', '.', date_str)

        # Parse the date using a flexible format (handling both two-digit and full years)
        if len(normalized_date.split('.')[-1]) == 2:  # Two-digit year
            date_obj = datetime.strptime(normalized_date, '%d.%m.%y')
        else:  # Full year
            date_obj = datetime.strptime(normalized_date, '%d.%m.%Y')

        # Return the formatted date as 'YYYY-MM-DD'
        return date_obj.strftime('%Y-%m-%d')

    except ValueError:
        # Handle cases where the date cannot be parsed
        print(f"Error converting date: {date_str}")
        return None