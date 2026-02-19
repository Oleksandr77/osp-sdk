import os
import json
import shutil
import argparse

def organize_photos(directory):
    report_path = os.path.join(directory, "analysis_report.json")
    
    if not os.path.exists(report_path):
        print(f"Error: Report file not found at {report_path}")
        return

    print(f"Reading analysis report from {report_path}...")
    with open(report_path, 'r') as f:
        data = json.load(f)

    # Define category mappings
    FOLDER_MAPPING = {
        "Photo (HEIC)": "Photos",
        "Photo (EXIF Verified)": "Photos",
        "Likely Photo (Has Date)": "Photos",
        
        "Screenshot (Filename)": "Screenshots",
        "Likely Screenshot (Resolution)": "Screenshots",
        "Graphic/Screenshot (PNG)": "Screenshots",
        
        "Likely Scan (Filename)": "Scans_Documents",
        "Likely Scan (A4 Ratio)": "Scans_Documents",
        
        "Unclassified/Other": "Other"
    }

    stats = {
        "Photos": 0,
        "Screenshots": 0,
        "Scans_Documents": 0,
        "Other": 0
    }

    print("Moving files into category folders...")

    for item in data:
        original_path = item['path']
        category = item['category']
        
        # Determine target folder
        target_folder_name = FOLDER_MAPPING.get(category, "Other")
        target_folder_path = os.path.join(directory, target_folder_name)
        
        # Create folder if it doesn't exist
        if not os.path.exists(target_folder_path):
            os.makedirs(target_folder_path)
            
        # Move file
        if os.path.exists(original_path):
            filename = os.path.basename(original_path)
            destination_path = os.path.join(target_folder_path, filename)
            
            # Handle duplicates if file already exists in destination
            if os.path.exists(destination_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(os.path.join(target_folder_path, f"{base}_{counter}{ext}")):
                    counter += 1
                destination_path = os.path.join(target_folder_path, f"{base}_{counter}{ext}")

            try:
                shutil.move(original_path, destination_path)
                stats[target_folder_name] += 1
            except Exception as e:
                print(f"Error moving {original_path}: {e}")
        else:
            print(f"Warning: File not found {original_path}")

    print("\n" + "="*40)
    print("ORGANIZATION COMPLETE")
    print("="*40)
    for folder, count in stats.items():
        print(f"{folder}: {count} files moved")
    print("="*40)
    print(f"Files are organized inside: {directory}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organize photos based on analysis report.")
    parser.add_argument("--dir", required=True, help="Directory containing photos and analysis_report.json")
    args = parser.parse_args()
    
    organize_photos(args.dir)
