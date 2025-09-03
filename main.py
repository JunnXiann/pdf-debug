import fitz  # PyMuPDF
import re

def extract_image_matrices(pdf_path):
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

def main():
    extract_image_matrices("初字第07册.pdf")

if __name__ == "__main__":
    main()