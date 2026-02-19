from googleapiclient.discovery import build
from auth import get_credentials
import argparse

def analyze_drive_photos(profile_name):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('drive', 'v3', credentials=creds)

    print("Searching for image files in Google Drive...")
    print("This might take a while if you have many files...")

    # Query for images, not trashed
    query = "mimeType contains 'image/' and trashed = false"
    
    page_token = None
    total_count = 0
    total_size = 0
    images_by_year = {}

    while True:
        try:
            results = service.files().list(
                q=query,
                pageSize=1000,
                fields="nextPageToken, files(id, name, size, createdTime, mimeType)",
                pageToken=page_token
            ).execute()

            files = results.get('files', [])
            
            for file in files:
                total_count += 1
                if 'size' in file:
                    total_size += int(file['size'])
                
                # Categorize by year
                if 'createdTime' in file:
                    year = file['createdTime'][:4]
                    images_by_year[year] = images_by_year.get(year, 0) + 1

            page_token = results.get('nextPageToken')
            print(f"Processed {total_count} images so far...", end='\r')
            
            if not page_token:
                break
                
        except Exception as e:
            print(f"\nError during search: {e}")
            break

    def sizeof_fmt(num, suffix="B"):
        for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
            if abs(num) < 1024.0:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.1f}Pi{suffix}"

    print(f"\n\nAnalysis Complete for {profile_name}!")
    print("="*40)
    print(f"Total Image Files: {total_count}")
    print(f"Total Size: {sizeof_fmt(total_size)}")
    print("="*40)
    print("Images by Year:")
    for year in sorted(images_by_year.keys(), reverse=True):
        print(f"{year}: {images_by_year[year]} images")
    print("="*40)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze photos in Google Drive.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    args = parser.parse_args()
    
    analyze_drive_photos(args.profile)
