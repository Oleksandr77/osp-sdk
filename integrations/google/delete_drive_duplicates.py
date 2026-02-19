from googleapiclient.discovery import build
from auth import get_credentials
import argparse
from collections import defaultdict

def delete_drive_duplicates(profile_name, dry_run=True):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('drive', 'v3', credentials=creds)

    print("Scanning for duplicates to delete...")
    
    query = "mimeType contains 'image/' and trashed = false"
    
    page_token = None
    md5_map = defaultdict(list)
    
    # 1. Scan
    while True:
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="nextPageToken, files(id, name, size, md5Checksum, createdTime)",
            pageToken=page_token
        ).execute()

        files = results.get('files', [])
        for file in files:
            if 'md5Checksum' in file:
                md5_map[file['md5Checksum']].append(file)

        page_token = results.get('nextPageToken')
        print(f"Scanned {len(md5_map)} unique hashes...", end='\r')
        if not page_token:
            break
            
    # 2. Identify Duplicates
    to_delete = []
    wasted_size = 0
    
    print("\nidentifying duplicates...")
    for md5, files in md5_map.items():
        if len(files) > 1:
            # Sort by creation time (keep oldest)
            files.sort(key=lambda x: x.get('createdTime', ''))
            
            # Keep the first one (oldest), delete the rest
            original = files[0]
            duplicates = files[1:]
            
            for d in duplicates:
                to_delete.append(d)
                wasted_size += int(d.get('size', 0))

    def sizeof_fmt(num):
        for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
            if abs(num) < 1024.0: return f"{num:3.1f}{unit}B"
            num /= 1024.0
        return f"{num:.1f}PiB"

    print(f"\nFound {len(to_delete)} duplicate files.")
    print(f"Total separate reclaimable space: {sizeof_fmt(wasted_size)}")
    
    if len(to_delete) == 0:
        return

    if dry_run:
        print("\nDRY RUN: No files were deleted.")
        print("Use --confirm to actually delete files.")
        # Print first 5 examples
        for f in to_delete[:5]:
            print(f"Would delete: {f['name']} (ID: {f['id']})")
    else:
        print("\nDELETING FILES...")
        count = 0
        batch = service.new_batch_http_request()
        
        def callback(request_id, response, exception):
            if exception:
                print(f"Error deleting {request_id}: {exception}")
        
        # Process in chunks of 50
        chunk_size = 50
        for i in range(0, len(to_delete), chunk_size):
            chunk = to_delete[i:i+chunk_size]
            batch = service.new_batch_http_request()
            for f in chunk:
                batch.add(service.files().delete(fileId=f['id']), callback=callback)
            batch.execute()
            count += len(chunk)
            print(f"Deleted {count}/{len(to_delete)} files...", end='\r')
            
        print("\nDeletion Complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Delete Drive duplicates.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    parser.add_argument('--confirm', action='store_true', help='Actually delete files')
    args = parser.parse_args()
    
    delete_drive_duplicates(args.profile, dry_run=not args.confirm)
