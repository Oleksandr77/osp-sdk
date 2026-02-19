import os
import argparse
from PIL import Image, ExifTags
from pillow_heif import register_heif_opener
import json
from collections import defaultdict
import datetime

# Register HEIF opener
register_heif_opener()

def get_exif_data(image):
    exif_data = {}
    try:
        if hasattr(image, '_getexif'):
            info = image._getexif()
            if info:
                for tag, value in info.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    exif_data[decoded] = value
    except Exception:
        pass
    return exif_data

def classify_image(file_path):
    filename = os.path.basename(file_path).lower()
    ext = os.path.splitext(filename)[1]
    
    # 1. Check extension
    if ext in ['.heic', '.heif']:
        return "Photo (HEIC)"
    
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            ratio = width / height if height else 0
            
            # 2. Check EXIF for Camera Model or DateTimeOriginal
            exif = get_exif_data(img)
            
            has_camera_info = 'Make' in exif or 'Model' in exif
            has_date_original = 'DateTimeOriginal' in exif
            
            if has_camera_info and has_date_original:
                 return "Photo (EXIF Verified)"
            
            # 3. Check for Screenshot indicators
            if "screenshot" in filename or "screen shot" in filename:
                return "Screenshot (Filename)"
            
            # Standard screen resolutions often imply screenshots
            screen_res = [(1920, 1080), (1366, 768), (1440, 900), (2560, 1440), (2880, 1800), (1280, 720), (750, 1334), (1242, 2208), (1125, 2436)]
            
            # Allow for portrait orientation too
            if (width, height) in screen_res or (height, width) in screen_res:
                if not has_camera_info: 
                    return "Likely Screenshot (Resolution)"
                
            # 4. Check for Scans based on Keywords or specific ratios
            if "scan" in filename or "doc" in filename:
                return "Likely Scan (Filename)"
            
            # A4 aspect ratio is roughly 1.414 (or 0.707)
            # Scans often don't have EXIF camera data
            if 1.4 < ratio < 1.43 or 0.7 < ratio < 0.72:
                if not has_camera_info:
                    return "Likely Scan (A4 Ratio)"
                    
            # 5. Default fallback based on format and size
            if ext == '.png':
                return "Graphic/Screenshot (PNG)"
            
            if has_date_original: 
                 return "Likely Photo (Has Date)"
                 
            return "Unclassified/Other"

    except Exception as e:
        return f"Error: {str(e)}"

def main(directory):
    stats = defaultdict(int)
    details = []
    
    print(f"Scanning directory: {directory}...")
    
    file_count = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif')):
                file_count += 1
                file_path = os.path.join(root, file)
                category = classify_image(file_path)
                stats[category] += 1
                details.append({
                    "path": file_path,
                    "category": category
                })
                
                if file_count % 50 == 0:
                    print(f"Processed {file_count} images...")

    print("\n" + "="*40)
    print("CLASSIFICATION SUMMARY")
    print("="*40)
    for category, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        print(f"{category}: {count}")
    print("="*40)
    print(f"Total Images Analyzed: {file_count}")
    
    # Save detailed report
    report_path = os.path.join(directory, "analysis_report.json")
    with open(report_path, 'w') as f:
        json.dump(details, f, indent=2)
    print(f"\nDetailed report saved to: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify images as Photos, Screenshots, or Scans.")
    parser.add_argument("--dir", required=True, help="Directory to analyze")
    args = parser.parse_args()
    
    main(args.dir)
