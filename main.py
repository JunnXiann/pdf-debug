import fitz  # PyMuPDF
import re
from PIL import Image
import numpy as np
import io

def extract_image_matrices(pdf_path): # Extract transformation matrices for images in the PDF
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        content_streams = page.get_contents()
        if content_streams:
            stream_data = b"".join([doc.xref_stream(xref) for xref in content_streams])
            stream_text = stream_data.decode("latin1", errors="ignore")
            # Find all transformation matrices and image draws
            pattern = r"([-\d\. ]+)\s+cm\s*/(Im\d+)\s+Do"
            matches = re.findall(pattern, stream_text)
            print(f"Page {page_num+1}:")
            for matrix_str, im_name in matches:
                matrix = [float(x) for x in matrix_str.strip().split()]
                print(f"  Image {im_name}: matrix={matrix}")

def extract_and_transform_images(pdf_path, output_dir): # Extract images, apply transformations, and save them
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        content_streams = page.get_contents()
        if content_streams:
            stream_data = b"".join([doc.xref_stream(xref) for xref in content_streams]) # raw binary content directly from pdf
            stream_text = stream_data.decode("latin1", errors="ignore") #  decode the binary stream into a string
            pattern = r"([-\d\. ]+)\s+cm\s*/(Im\d+)\s+Do" # regex to find transformation matrices and image names
            matches = re.findall(pattern, stream_text)
            for matrix_str, im_name in matches: 
                matrix = [float(x) for x in matrix_str.strip().split()]
                # Find image xref
                img_xref = None
                for xref in page.get_images(full=True):
                    if xref[7] == im_name: # xref[7] contains the image name
                        img_xref = xref[0] # xref[0] is the object ID
                        break
                if img_xref:
                    img_info = doc.extract_image(img_xref)
                    img_bytes = img_info["image"]
                    img = Image.open(io.BytesIO(img_bytes))
                    a, b, c, d, e, f = matrix
                    # Calculate rotation angle from matrix
                    angle = np.degrees(np.arctan2(b, a))

                    img_rot = img.rotate(angle, expand=True, fillcolor=255)
                    # uncomment the following line to save images with white fill
                    # img_rot.save(f"{output_dir}/page{page_num+1}_{im_name}_fill.png") 

def main():
    # extract_image_matrices("初字第07册.pdf")
    extract_and_transform_images("初字第07册.pdf", "images_fill")

if __name__ == "__main__":
    main()