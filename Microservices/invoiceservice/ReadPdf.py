# shared/ReadPdf.py

import fitz  # PyMuPDF
from PIL import Image
import os

def pdf_to_jpg(pdf_path, file_name, output_folder):
    """
    Converts the first page of a PDF to a JPG image and saves it to output_folder.
    """
    pdf_document = fitz.open(pdf_path)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for page_number in range(len(pdf_document)):
        page = pdf_document.load_page(page_number)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        jpg_filename = f"{output_folder}/{file_name}_page{page_number + 1}.jpg"
        img.save(jpg_filename, "JPEG")
        print(f"Page {page_number + 1} saved as {jpg_filename}")

    pdf_document.close()
    return jpg_filename
