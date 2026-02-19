from googleapiclient.discovery import build
from auth import get_credentials
import argparse
from collections import defaultdict

def move_drive_duplicates(profile_name, dry_run=True):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('drive', 'v3', credentials=creds)

    print("Scanning for duplicates to move...")
    query = "mimeType contains 'image/' and trashed = false"
    
    page_token = None
    md5_map = defaultdict(list)
    
    # 1. Scan
    while True:
        try:
            results = service.files().list(
                q=query,
                pageSize=1000,
                fields="nextPageToken, files(id, name, size, md5Checksum, createdTime, parents)",
                pageToken=page_token
            ).execute()
        except Exception as e:
            print(f"Error scanning: {e}")
            break

        files = results.get('files', [])
        for file in files:
            if 'md5Checksum' in file:
                md5_map[file['md5Checksum']].append(file)

        page_token = results.get('nextPageToken')
        print(f"Scanned {len(md5_map)} unique hashes...", end='\r')
        if not page_token:
            break
            
    # 2. Identify Duplicates
    to_move = []
    
    print("\nIdentifying duplicates...")
    for md5, files in md5_map.items():
        if len(files) > 1:
            # Sort by creation time (keep oldest)
            files.sort(key=lambda x: x.get('createdTime', ''))
            
            # Keep the first one (oldest), move the rest
            # original = files[0]
            duplicates = files[1:]
            
            for d in duplicates:
                to_move.append(d)

    print(f"\nFound {len(to_move)} duplicate files to move.")
    
    if len(to_move) == 0:
        return

    # 3. Create/Get Duplicates Folder
    target_folder_id = None
    folder_name = "!Duplicates_Antigravity"
    
    if not dry_run:
        q = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        res = service.files().list(q=q).execute()
        if res.get('files'):
            target_folder_id = res['files'][0]['id']
        else:
            print(f"Creating folder: {folder_name}")
            meta = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            f = service.files().create(body=meta, fields='id').execute()
            target_folder_id = f['id']

    if dry_run:
        print("\nDRY RUN: Files will be moved to '!Duplicates_Antigravity'.")
        print("Use --confirm to actually move files.")
        for f in to_move[:5]:
            print(f"Would move: {f['name']} (ID: {f['id']})")
    else:
        print(f"\nMoving {len(to_move)} files to folder '{folder_name}' ({target_folder_id})...")
        
        batch = service.new_batch_http_request()
        count = 0
        
        def callback(request_id, response, exception):
            if exception: print(f"Error moving {request_id}: {exception}")

        chunk_size = 50
        for i in range(0, len(to_move), chunk_size):
            chunk = to_move[i:i+chunk_size]
            batch = service.new_batch_http_request()
            
            for f in chunk:
                prev_parents = ",".join(f.get('parents', []))
                batch.add(service.files().update(fileId=f['id'], addParents=target_folder_id, removeParents=prev_parents), callback=callback)
            
            try:
                batch.execute()
                count += len(chunk)
                print(f"Moved {count}/{len(to_move)} files...", end='\r')
            except Exception as e:
                print(f"Batch error: {e}")

        print("\nMove Complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Move Drive duplicates.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    parser.add_argument('--confirm', action='store_true', help='Actually move files')
    args = parser.parse_args()
    
    move_drive_duplicates(args.profile, dry_run=not args.confirm)
