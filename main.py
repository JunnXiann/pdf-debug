import fitz  # PyMuPDF
import re
from PIL import Image
import numpy as np
import io
import os
import csv
import bson

def extract_image_matrices(pdf_path): # Extract transformation matrices for images in the PDF
    doc = fitz.open(pdf_path)
    skewed = {}
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        content_streams = page.get_contents()
        if content_streams:
            stream_data = b"".join([doc.xref_stream(xref) for xref in content_streams])
            stream_text = stream_data.decode("latin1", errors="ignore")
            # Find all transformation matrices and image draws
            pattern = r"([-\d\. ]+)\s+cm\s*/(Im\d+)\s+Do"
            matches = re.findall(pattern, stream_text)
            for matrix_str, im_name in matches:
                matrix = [float(x) for x in matrix_str.strip().split()]
                a, b, c, d, e, f = matrix
                angle = np.degrees(np.arctan2(b, a))
                label = orientation_label(angle)
                pagenum = page_num + 1
                if pagenum not in skewed:
                    skewed[pagenum] = []
                skewed[pagenum].append({"image": im_name, "angle": angle, "label": label})
                # if abs(angle) > degree and abs(angle - 180) > degree and abs(angle + 180) > degree: 
                #     pagenum = page_num + 1
                #     if pagenum not in skewed:
                #         skewed[pagenum] = []
                #     skewed[pagenum].append({"image": im_name, "angle": angle})
    return skewed

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
            print(matches)
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

def orientation_label(angle):
    a = abs(angle)
    if a < 1:
        return "正"
    elif a < 2:
        return "微倾"
    elif a >= 179:
        return "反转"
    elif a > 178:
        return "反转+微倾"
    else:
        return "倾斜"

def transformation_matrix_extractor(source_folder, threshold=0.5):
    with open('outlier.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['文件路径', '页码', '图片', '角度', '标签', '面积', '异常'])
        for dirpath, _, filenames in os.walk(source_folder):
            subdir = os.path.relpath(dirpath, source_folder)
            for filename in filenames:
                if filename.lower().endswith(".pdf"):
                    pdf_path = os.path.join(dirpath, filename)
                    print(f"Processing {pdf_path}")

                    # 1. Collect all image areas for this PDF
                    doc = fitz.open(pdf_path)
                    area_dict = {}
                    all_areas = []
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        images = page.get_images(full=True)
                        for img in images:
                            name = img[7]
                            bbox = page.get_image_bbox(name)
                            area = (bbox.x1 - bbox.x0) * (bbox.y1 - bbox.y0)
                            all_areas.append(area)
                            area_dict[(page_num + 1, name)] = area
                    if not all_areas:
                        continue
                    median_area = np.median(all_areas)
                    print(median_area)

                    # 2. Extract transformation matrices and write CSV with outlier label
                    skewed = extract_image_matrices(pdf_path)
                    for pagenum, images in skewed.items():
                        for img in images:
                            area = area_dict.get((pagenum, img['image']), 0)
                            ratio = area / median_area if median_area else 0
                            outlier = ""
                            if ratio < threshold or ratio > 1/threshold:
                                outlier = "异常"
                            writer.writerow([
                                f"{subdir}/{filename}",
                                pagenum,
                                img['image'],
                                f"{img['angle']:.2f}",
                                img['label'],
                                f"{area:.2f}",
                                outlier
                            ])

def extract_image(pdf_path, page_num, im_name=""):
    doc = fitz.open(pdf_path)
    print(pdf_path)
    page = doc.load_page(page_num)
    images = page.get_images(full=True)
    for img in images:
        if img[7] == im_name: # xref[7] contains the image name
            img_xref = img[0] # xref[0] is the object ID
            img_info = doc.extract_image(img_xref)
            img_bytes = img_info["image"]
            image = Image.open(io.BytesIO(img_bytes))
            # img_rot = img.rotate(-3.205464982, expand=True)
            image.save(f"{img[7]}.jpg")
    return None

def extract_matrixes(pdf_path): # Extract images, apply transformations, and save them
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        content_streams = page.get_contents()
        if content_streams:
            stream_data = b"".join([doc.xref_stream(xref) for xref in content_streams]) # raw binary content directly from pdf
            stream_text = stream_data.decode("latin1", errors="ignore") #  decode the binary stream into a string
            print(stream_text)
            pattern = r"([-\d\. ]+)\s+cm\s*/(Im\d+)\s+Do" # regex to find transformation matrices and image names
            matches = re.findall(pattern, stream_text)
            
def list_images(pdf_path, proximity=20):
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images(full=True)
        print(f"Page {page_num}:")
        for img in images:
            xref = img[0]
            name = img[7]
            img_info = doc.extract_image(xref)
            img_bytes = img_info["image"]
            image = Image.open(io.BytesIO(img_bytes))
            # bbox = page.get_image_bbox(name)
            image.save(f"test/image_{page_num}_{name}.jpeg")
            # print(f"  Image {name} (xref {xref}): bbox={bbox}")

def find_outlier_images(pdf_path, threshold=0.5):
    doc = fitz.open(pdf_path)
    all_areas = []
    image_info = []

    # Collect all image areas
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images(full=True)
        for img in images:
            name = img[7]
            bbox = page.get_image_bbox(name)
            area = (bbox.x1 - bbox.x0) * (bbox.y1 - bbox.y0)
            all_areas.append(area)
            image_info.append({
                "page": page_num + 1,
                "name": name,
                "bbox": bbox,
                "area": area
            })

    if not all_areas:
        print("No images found.")
        return

    # Calculate median area
    median_area = np.median(all_areas)

    # Find outliers
    print(f"Median area: {median_area:.2f}")
    print("Potential outlier images (area < {0:.0%} or > {1:.0%} of median):".format(threshold, 1/threshold))
    for info in image_info:
        ratio = info["area"] / median_area
        if ratio < threshold or ratio > 1/threshold:
            print(f"Page {info['page']} Image {info['name']} area={info['area']:.2f} (ratio={ratio:.2f}) bbox={info['bbox']}")

def main():
    # extract_image_matrices("初字第07册.pdf", 1)
    # extract_and_transform_images("初字第07册.pdf", "images_fill")
    # transformation_matrix_extractor("../思溪藏_扬州古籍_PDF(最终)")
    # extract_image("../../02_Data/思溪藏_扬州古籍_PDF/135/食字第07册.pdf", 0, "Im1")
    # extract_matrixes("../../02_Data/思溪藏_扬州古籍_PDF/097/吊字第10册.pdf")
    list_images("../../02_Data/思溪藏_扬州古籍_PDF/104/汤字第03册.pdf")
    # find_outlier_images("../../02_Data/思溪藏_扬州古籍_PDF/097/吊字第10册.pdf")
    # transformation_matrix_extractor("../../02_Data/思溪藏_扬州古籍_PDF", threshold=0.5)

    # print(orientation_label(-179.00))

if __name__ == "__main__":
    main()