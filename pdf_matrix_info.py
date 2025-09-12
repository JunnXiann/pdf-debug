import fitz
import os
import re
import csv
import numpy as np
from PIL import Image

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

def collect_image_areas(pdf_path):
    doc = fitz.open(pdf_path)
    area_dict = {}
    all_areas = []
    bbox_dict = {}
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        for img in page.get_images(full=True):
            name = img[7]
            bbox = page.get_image_bbox(name)
            area = (bbox.x1 - bbox.x0) * (bbox.y1 - bbox.y0)
            area_dict[(page_num, name)] = area
            bbox_dict[(page_num, name)] = bbox
            all_areas.append(area)
    return area_dict, all_areas, bbox_dict

def sort_images_by_position(bbox_dict, page_num):
    """Sort images by position to match the sequential ordering (0,1,2,3...9)"""
    page_images = [(name, bbox) for (pnum, name), bbox in bbox_dict.items() if pnum == page_num]
    
    if not page_images:
        return {}
    
    # Get actual min and max y coordinates of all images
    min_y = min(bbox.y0 for _, bbox in page_images)
    max_y = max(bbox.y1 for _, bbox in page_images)
    page_mid_y = (min_y + max_y) / 2
    
    # Separate upper and lower half images based on their center point
    upper_images = []
    lower_images = []
    
    for name, bbox in page_images:
        bbox_center_y = (bbox.y0 + bbox.y1) / 2
        if bbox_center_y < page_mid_y:
            upper_images.append((name, bbox))
        else:
            lower_images.append((name, bbox))
    
    # Sort by x-coordinate (left to right)
    upper_images.sort(key=lambda x: x[1].x0)
    lower_images.sort(key=lambda x: x[1].x0)
    
    # Create position mapping
    position_map = {}
    current_pos = 0
    
    # Upper row images (0, 1, 2, 3, 4)
    for name, bbox in upper_images:
        position_map[name] = current_pos
        current_pos += 1
    
    # Lower row images (5, 6, 7, 8, 9)
    for name, bbox in lower_images:
        position_map[name] = current_pos
        current_pos += 1
    
    return position_map
  

def extract_image_transformations(pdf_path):
    doc = fitz.open(pdf_path)
    skewed = {}
    bbox_dict = {}
    
    # First collect bbox info
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        for img in page.get_images(full=True):
            name = img[7]
            bbox = page.get_image_bbox(name)
            bbox_dict[(page_num, name)] = bbox
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        content_streams = page.get_contents()
        if content_streams:
            stream_data = b"".join([doc.xref_stream(xref) for xref in content_streams])
            stream_text = stream_data.decode("latin1", errors="ignore")
            pattern = r"([-\d\. ]+)\s+cm\s*/(Im\d+)\s+Do"
            matches = re.findall(pattern, stream_text)
            
            # Get position mapping for this page
            position_map = sort_images_by_position(bbox_dict, page_num)
            
            for matrix_str, im_name in matches:
                matrix = [float(x) for x in matrix_str.strip().split()]
                a, b, c, d, e, f = matrix
                angle = np.degrees(np.arctan2(b, a))
                label = orientation_label(angle)
                position = position_map.get(im_name, 0)  # Default to 0 if not found
                
                if page_num not in skewed:
                    skewed[page_num] = []
                skewed[page_num].append({
                    "image": im_name, 
                    "angle": angle, 
                    "label": label, 
                    "position": position
                })
    
    return skewed

def label_outliers(area_dict, all_areas, threshold=0.5):
    median_area = np.median(all_areas) if all_areas else 0
    outlier_dict = {}
    for key, area in area_dict.items():
        ratio = area / median_area if median_area else 0
        outlier = ""
        if ratio < threshold or ratio > 1/threshold:
            outlier = "异常"
        outlier_dict[key] = (area, outlier)
    return outlier_dict, median_area

def write_csv(rows, csv_path):
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['文件路径', '页码', '图片', '角度', '标签', '面积', 'bid', '异常', 'bbox', '位置'])
        for row in rows:
            writer.writerow(row)

def extract_volume_number(filename):
    match = re.search(r'(\d+)册\.pdf$', filename)
    if match:
        return int(match.group(1))
    return None

def extract_image_number(im_name):
    match = re.match(r'Im(\d+)', im_name)
    if match:
        return int(match.group(1))
    return None

def process_pdf(pdf_path, subdir, filename, threshold=0.5):
    dir = int(subdir)
    vol = extract_volume_number(filename)
    area_dict, all_areas, bbox_dict = collect_image_areas(pdf_path)
    if not all_areas:
        return []
    outlier_dict, median_area = label_outliers(area_dict, all_areas, threshold)
    skewed = extract_image_transformations(pdf_path)
    rows = []
    for pagenum, images in skewed.items():
        for img in images:
            key = (pagenum, img['image'])
            area, outlier = outlier_dict.get(key, (0, ""))
            bbox = bbox_dict.get(key)
            bbox_str = f"({bbox.x0:.2f}, {bbox.y0:.2f}, {bbox.x1:.2f}, {bbox.y1:.2f})" if bbox else ""
            bid = f"{dir}_{vol}_{pagenum}_{img['position']}"
            rows.append([
                f"{subdir}/{filename}",
                pagenum,
                img['image'],
                f"{img['angle']:.2f}",
                img['label'],
                f"{area:.2f}",
                bid,
                outlier,
            ])
    return rows

def transformation_matrix_extractor(source_folder, threshold=0.5, csv_path='bids.csv', max_files=None):
    all_rows = []
    file_count =  0
    for dirpath, _, filenames in os.walk(source_folder):
        subdir = os.path.relpath(dirpath, source_folder)
        for filename in filenames:
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(dirpath, filename)
                print(f"Processing {pdf_path}")
                rows = process_pdf(pdf_path, subdir, filename, threshold)
                all_rows.extend(rows)
                file_count += 1
                if max_files is not None and file_count >= max_files:
                    break
    write_csv(all_rows, csv_path)

if __name__ == "__main__":
    transformation_matrix_extractor("../../02_Data/思溪藏_扬州古籍_PDF", threshold=0.5)