import fitz  # PyMuPDF
import re
def extract_text_from_pdf(pdf_path):
    file=pdf_path
    doc = fitz.open(pdf_path)  # Open the PDF file
    extracted_text = ""

    for page in doc:  # Loop through all pages
        extracted_text += page.get_text("text") + "\n\n"  # Extract text
    #extracted_text = " ".join(extracted_text.split())
    print(extracted_text)
    doc.close()
    return extracted_text

def format_receipt_text_old(text):
    """
    Format receipt text:
    1. Fix 'EUR / kg' breaking into two lines.
    2. Ensure each item starts on a new line when price with 'A' or 'B' is detected.
    3. Ensure product names that start with uppercase letters go to a new line.

    Args:
        text (str): Raw extracted text from the receipt.

    Returns:
        str: Properly formatted receipt text.
    """

    # Ensure consistent spacing
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'(Peterson Warenhandels GmbH&Co.KG)', r'\1\n', text)
    text = re.sub(r'(Schönwalder Straße \d+ \d{5} Berlin/Spandau)', r'\1\n', text)
    text = re.sub(r'(UID Nr\.: DE\d+)', r'\1\n', text)
    # Fix EUR/kg issue by merging split parts
    text = re.sub(r'(\d+,\d+\s+EUR)\s*/?\s*kg', r'\1/kg', text)  # Ensures EUR/kg stays together
    text = re.sub(r'(EUR/kg)\s+([A-ZÄÖÜ].+? [\d,]+ [AB])', r'\1\n\2', text)
    text = re.sub(r'([+-]?\d+[\s,.]\d{2})(?=\s+[A-B])\s+([A-B])', r'\1 \2\n', text)
    # Ensure item separation: Add a newline before price values (X,XX A or X,XX B)
    #text = re.sub(r'(\d+,\d+\s+[AB])', r'\n\1', text)  # Ensures items with price A/B start on a new line

    # Fix "JA!" and other uppercase product names appearing on the same line
    text = re.sub(r'(\d+,\d+\s+[AB])\s+(JA!|[A-ZÄÖÜ].+)', r'\1\n\2', text)
    # Move new product names to a new line if they appear after '2 Stk x 0,99'
    text = re.sub(r'(2 Stk x \d+,\d+)\s+([A-ZÄÖÜ].+? [\d,]+ [AB])', r'\1\n\2', text)
    # Clean up excess spaces after newline insertions
    text = re.sub(r'\n\s+', '\n', text)
    # Remove unwanted symbols like dashes and equal signs
    text = re.sub(r'-{5,}', '', text)  # Removes long dashes (-----)
    text = re.sub(r'={5,}', '', text)  # Removes long equal signs (=====)

    return text.strip()


def format_receipt_text(text):
    """
    Format receipt text:
    1. Fix 'EUR/kg' breaking items into the same line.
    2. Ensure each item starts on a new line when a price with 'A' or 'B' is detected.
    3. Keep '2 Stk x 0,99' together with its related item.
    4. Ensure product names (like "LAYS KRAEUTERBUT") go to a new line if they follow '2 Stk x 0,99'.

    Args:
        text (str): Raw extracted text from the receipt.

    Returns:
        str: Properly formatted receipt text.
    """

    # Ensure consistent spacing
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'REWE', r'REWE\n', text)

    text = re.sub(r'(Peterson Warenhandels GmbH&Co.KG)', r'\1\n', text)
    text = re.sub(r'(Schönwalder Straße \d+ \d{5} Berlin/Spandau)', r'\1\n', text)
    text = re.sub(r'(UID Nr\.: DE\d+)', r'\1\n', text)
    # Fix EUR/kg issue by merging split parts
    text = re.sub(r'(\d+,\d+\s+EUR)\s*/?\s*kg', r'\1/kg', text)  # Ensures EUR/kg stays together

    # Ensure that if a line ends with EUR/kg, the next item moves to a new line
    text = re.sub(r'(EUR/kg)\s+([A-ZÄÖÜ].+? [\d,]+ [AB])', r'\1\n\2', text)

    # Ensure item separation: Add a newline before price values (X,XX A or X,XX B)
    #text = re.sub(r'(\d+,\d+\s+[AB])', r'\n\1', text)  # Ensures items with price A/B start on a new line
    text = re.sub(r'([+-]?\d+[\s,.]\d{2})(?=\s+[A-B])\s+([A-B])', r'\1 \2\n', text)
    # Move new product names to a new line if they appear after '2 Stk x 0,99'
    # Keep 'Price A/B + Quantity' together on the same line
    text = re.sub(r'(\d+,\d+\s+[AB])\s+(?=\d+\s+Stk\s+x\s+\d+,\d+)', r'\1 ', text)
    text = re.sub(r'(\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4})',r'\n\1\n ', text)
    # Keep 'Price A/B + Weight-based Pricing' together on the same line
    text = re.sub(r'(\d+,\d+\s+[AB])\s+(?=\d+,\d+\s+kg\s+x\s+\d+,\d+\s+EUR/kg)', r'\1 ', text)
    # Move next product name to a new line if it follows 'A/B X Stk x X,XX'
    text = re.sub(r'(\d+,\d+\s+[AB]\s+\d+\s+Stk\s+x\s+\d+,\d+)\s+([A-ZÄÖÜ].+? [\d,]+ [AB])', r'\1\n\2', text)
    # Clean up excess spaces after newline insertions
    text = re.sub(r'\n\s+', '\n', text)
    text = re.sub(r'-{5,}', '', text)  # Removes long dashes (-----)
    text = re.sub(r'={5,}', '', text)
    return text.strip()

import fitz  # PyMuPDF
import re

def extract_rewe_receipt_details(pdf_path):
    doc = fitz.open(pdf_path)  # Open the PDF file
    extracted_text = "\n".join([page.get_text("text") for page in doc])  # Extract text from all pages
    print(extracted_text)
    doc.close()  # Close PDF

    # Extract Store Address
    store_match = re.search(r'(\d{5} Berlin\S*)', extracted_text)
    store_address = f"Schönwalder Straße 32, {store_match.group(1)}" if store_match else "Not Found"

    # Extract Date, Time, and Receipt Number
    date_match = re.search(r'Datum:\s+(\d{2}.\d{2}.\d{4})', extracted_text)
    time_match = re.search(r'Uhrzeit:\s+(\d{2}:\d{2}:\d{2} Uhr)', extracted_text)
    receipt_match = re.search(r'Beleg-Nr\.\s+(\d+)', extracted_text)

    date = date_match.group(1) if date_match else "Not Found"
    time = time_match.group(1) if time_match else "Not Found"
    receipt_number = receipt_match.group(1) if receipt_match else "Not Found"

    # Extract Purchased Items with Quantity and Price
    item_pattern = re.findall(r'([A-ZÄÖÜa-zäöüß\s.-]+)\s+([\d]+)\s*Stk*\s*x*\s*([\d,.]+)\s*EUR/kg*\s*\n*([\d,.]+)\s+[AB]', extracted_text)
    items = []

    for item in item_pattern:
        items.append({
            "item": item[0].strip(),
            "quantity": int(item[1]),
            "unit_price": item[2],
            "total_price": item[3]
        })

    # Extract Total Amount & Payment Details
    total_match = re.search(r'SUMME\s+EUR\s+([\d,.]+)', extracted_text)
    bonus_match = re.search(r'Geg\. Bonus-Guthaben\s+EUR\s+([\d,.]+)', extracted_text)
    mastercard_match = re.search(r'Geg\. Mastercard\s+EUR\s+([\d,.]+)', extracted_text)
    card_number_match = re.search(r'Mastercard\s+Nr\.\s+############(\d{4})', extracted_text)

    total_amount = total_match.group(1) if total_match else "Not Found"
    bonus_used = bonus_match.group(1) if bonus_match else "0.00"
    mastercard_paid = mastercard_match.group(1) if mastercard_match else "0.00"
    card_number = f"**** **** **** {card_number_match.group(1)}" if card_number_match else "Not Found"

    # Format results
    receipt_data = {
        "Store Address": store_address,
        "Date": date,
        "Time": time,
        "Receipt Number": receipt_number,
        "Purchased Items": items,
        "Total Amount": f"EUR {total_amount}",
        "Bonus Used": f"EUR {bonus_used}",
        "Paid via Mastercard": f"EUR {mastercard_paid}",
        "Card Used": card_number
    }

    return receipt_data

def extract_rewe_receipt_details(pdf_path):
    doc = fitz.open(pdf_path)  # Open the PDF file
    extracted_text = "\n".join([page.get_text("text") for page in doc])  # Extract text from all pages
    doc.close()  # Close PDF

    # Extract Store Address
    store_match = re.search(r'(\d{5} Berlin\S*)', extracted_text)
    store_address = f"Schönwalder Straße 32, {store_match.group(1)}" if store_match else "Not Found"

    # Extract Date, Time, and Receipt Number
    date_match = re.search(r'Datum:\s+(\d{2}.\d{2}.\d{4})', extracted_text)
    time_match = re.search(r'Uhrzeit:\s+(\d{2}:\d{2}:\d{2} Uhr)', extracted_text)
    receipt_match = re.search(r'Beleg-Nr\.\s+(\d+)', extracted_text)

    date = date_match.group(1) if date_match else "Not Found"
    time = time_match.group(1) if time_match else "Not Found"
    receipt_number = receipt_match.group(1) if receipt_match else "Not Found"

    # **Extract Regular Items (Name, Price)**
    item_pattern = re.findall(r'([A-ZÄÖÜa-zäöüß\s.-]+)\s+([\d,.]+)\s+[AB]', extracted_text)
    items = []

    for item in item_pattern:
        items.append({
            "item": item[0].strip(),
            "quantity": 1,  # Default quantity for single items
            "unit_price": item[1],
            "total_price": item[1]
        })

    # **Extract Weight-Based Items (like Kartoffeln)**
    weight_pattern = re.findall(r'([A-ZÄÖÜa-zäöüß\s.-]+)\s*\n\s*([\d,.]+)\s*kg x\s*([\d,.]+)\s*EUR/kg', extracted_text)

    for item in weight_pattern:
        total_price = round(float(item[1].replace(',', '.')) * float(item[2].replace(',', '.')), 2)
        items.append({
            "item": item[0].strip(),
            "quantity": item[1],  # Weight in kg
            "unit_price": item[2],  # Price per kg
            "total_price": f"{total_price:.2f}"
        })

    # Extract Total Amount & Payment Details
    total_match = re.search(r'SUMME\s+EUR\s+([\d,.]+)', extracted_text)
    bonus_match = re.search(r'Geg\. Bonus-Guthaben\s+EUR\s+([\d,.]+)', extracted_text)
    mastercard_match = re.search(r'Geg\. Mastercard\s+EUR\s+([\d,.]+)', extracted_text)
    card_number_match = re.search(r'Mastercard\s+Nr\.\s+############(\d{4})', extracted_text)

    total_amount = total_match.group(1) if total_match else "Not Found"
    bonus_used = bonus_match.group(1) if bonus_match else "0.00"
    mastercard_paid = mastercard_match.group(1) if mastercard_match else "0.00"
    card_number = f"**** **** **** {card_number_match.group(1)}" if card_number_match else "Not Found"

    # Format results
    receipt_data = {
        "Store Address": store_address,
        "Date": date,
        "Time": time,
        "Receipt Number": receipt_number,
        "Purchased Items": items,
        "Total Amount": f"EUR {total_amount}",
        "Bonus Used": f"EUR {bonus_used}",
        "Paid via Mastercard": f"EUR {mastercard_paid}",
        "Card Used": card_number
    }

    return receipt_data



