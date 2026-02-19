from googleapiclient.discovery import build
from auth import get_credentials
import argparse
from collections import defaultdict

def analyze_drive_duplicates(profile_name):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('drive', 'v3', credentials=creds)

    print("Scanning Drive files for duplicates (checking hashes and metadata)...")
    
    query = "mimeType contains 'image/' and trashed = false"
    
    page_token = None
    processed_count = 0
    
    # Storage for analysis
    md5_map = defaultdict(list) # md5 -> [file_info]
    name_map = defaultdict(list) # name -> [file_info]
    time_map = defaultdict(list) # createTime/metaTime -> [file_info]

    while True:
        try:
            # Request md5Checksum and imageMediaMetadata
            results = service.files().list(
                q=query,
                pageSize=1000,
                fields="nextPageToken, files(id, name, size, md5Checksum, createdTime, imageMediaMetadata)",
                pageToken=page_token
            ).execute()

            files = results.get('files', [])
            
            for file in files:
                processed_count += 1
                
                f_info = {
                    'id': file.get('id'),
                    'name': file.get('name'),
                    'size': int(file.get('size', 0)),
                    'time': file.get('createdTime')
                }
                
                # Check MD5 (Exact Binary Duplicate)
                if 'md5Checksum' in file:
                    md5_map[file['md5Checksum']].append(f_info)
                
                # Check Name (Potential version/quality diff)
                if 'name' in file:
                    name_map[file['name']].append(f_info)

                # Check EXIF Time (Best for finding same photo with different quality)
                # imageMediaMetadata.time is when the photo was taken
                meta = file.get('imageMediaMetadata', {})
                if meta and 'time' in meta:
                    time_map[meta['time']].append(f_info)

            page_token = results.get('nextPageToken')
            print(f"Scanned {processed_count} files...", end='\r')
            
            if not page_token:
                break
                
        except Exception as e:
            print(f"\nError: {e}")
            break

    print(f"\n\nAnalysis Complete. Found {processed_count} total images.")
    
    # Analyze Exact Duplicates
    exact_dupes_count = 0
    exact_dupes_wasted_size = 0
    for md5, files in md5_map.items():
        if len(files) > 1:
            exact_dupes_count += (len(files) - 1)
            # Size is same for all in this group
            exact_dupes_wasted_size += files[0]['size'] * (len(files) - 1)

    # Analyze "Quality" Duplicates (Same capture time, different hash/size)
    quality_dupes_count = 0
    possible_quality_dupes = []
    
    for capture_time, files in time_map.items():
        if len(files) > 1:
            # Check if they have different MD5s (meaning different files, possibly different quality)
            # If MD5s are same, they are exact dupes (already counted)
            
            # Group by size to see variations
            sizes = defaultdict(list)
            for f in files:
                sizes[f['size']].append(f)
            
            # If we have more than 1 distinct size for the same timestamp, it's likely a quality duplicate
            if len(sizes) > 1:
                quality_dupes_count += 1
                # Just keep a few examples
                if len(possible_quality_dupes) < 5:
                    possible_quality_dupes.append({
                        'time': capture_time,
                        'variations': [f"{f['name']} ({sizeof_fmt(f['size'])})" for f in files]
                    })

    print("\n" + "="*40)
    print("DUPLICATE REPORT")
    print("="*40)
    print(f"1. EXACT Duplicates (Identical files):")
    print(f"   - Count: {exact_dupes_count} files are copies")
    print(f"   - Wasted Space: {sizeof_fmt(exact_dupes_wasted_size)}")
    
    print(f"\n2. PROBABLE VISUAL/QUALITY Duplicates:")
    print(f"   (Different files detected with exact same capture timestamp)")
    print(f"   - Groups found: {quality_dupes_count}")
    
    if possible_quality_dupes:
        print("\n   Examples of quality differences:")
        for item in possible_quality_dupes:
            print(f"   - Time: {item['time']}")
            for var in item['variations']:
                print(f"     * {var}")

def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Pi{suffix}"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze Drive duplicates.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    args = parser.parse_args()
    
    analyze_drive_duplicates(args.profile)
