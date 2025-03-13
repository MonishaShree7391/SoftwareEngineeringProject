import fitz  # PyMuPDF
from PIL import Image

def extract_images_from_pdf(pdf_path, file_name, output_folder):
    pdf_document = fitz.open(pdf_path)
    image_index = 0
    print('pdf_path: ',pdf_path)
    print('file_name: ',file_name)
    print('output_folder: ',output_folder)

    for page_index in range(len(pdf_document)):
        page = pdf_document[page_index]
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_path = f"{output_folder}/{file_name}_image.{image_ext}"
            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)
            image_index += 1
    print(image_path)
    return image_path

def pdf_to_jpg(pdf_path,file_name, output_folder):
    # Open the provided PDF file
    pdf_document = fitz.open(pdf_path)

    # Iterate through each page in the PDF
    for page_number in range(len(pdf_document)):
        # Get the page
        page = pdf_document.load_page(page_number)

        # Render the page as an image (you can increase resolution if needed)
        pix = page.get_pixmap()

        # Convert the pixmap to RGB (3x8 bits per pixel)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Save the image as a JPG file
        jpg_filename = f"{output_folder}/{file_name}_image.jpg"
        img.save(jpg_filename, "JPEG")
        print(f"Page {page_number + 1} saved as {jpg_filename}")

    # Close the PDF document
    pdf_document.close()
    return jpg_filename

def extract_text_from_pdf(pdf_path,filename):


    full_path = pdf_path
    print(full_path)
    #full_path_with_extension = full_path + ".pdf"
    doc = fitz.open(pdf_path)  # Open the PDF file
    extracted_text = ""

    for page in doc:  # Loop through all pages
        extracted_text += page.get_text("text") + "\n\n"  # Extract text
    extracted_text = " ".join(extracted_text.split())
    doc.close()
    return extracted_text