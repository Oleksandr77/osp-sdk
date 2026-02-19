from googleapiclient.discovery import build
from .auth import get_credentials
import argparse
import time

def organize_drive_files(profile_name, dry_run=True):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('drive', 'v3', credentials=creds)

    print("Scanning Drive based on mimeType (Images)...")
    # Only organize images for now to avoid messing up other docs
    query = "mimeType contains 'image/' and trashed = false and 'root' in parents" 
    # Note: 'root' in parents ensures we only move files from the root, not inside existing folders!
    # This is safer than moving everything.
    
    files_to_move = []
    page_token = None
    
    while True:
        try:
            results = service.files().list(
                q=query,
                pageSize=1000,
                fields="nextPageToken, files(id, name, createdTime, parents)",
                pageToken=page_token
            ).execute()
            
            files_to_move.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            print(f"Found {len(files_to_move)} files in Root...", end='\r')
            if not page_token: break
        except Exception as e:
            print(f"Error scanning: {e}")
            break
            
    print(f"\nFound {len(files_to_move)} images in Root directory to organize.")
    
    if len(files_to_move) == 0:
        print("No images found in Root to organize.")
        return

    # Cache folder IDs
    folder_cache = {} # "2024" -> ID, "2024/05-May" -> ID
    
    def get_or_create_folder(year, month_name):
        # 1. Year Folder
        if year not in folder_cache:
            # Check if exists
            q = f"mimeType='application/vnd.google-apps.folder' and name='{year}' and trashed=false and 'root' in parents"
            res = service.files().list(q=q).execute()
            if res.get('files'):
                folder_cache[year] = res['files'][0]['id']
            else:
                if not dry_run:
                    print(f"Creating folder: {year}")
                    meta = {'name': year, 'mimeType': 'application/vnd.google-apps.folder'}
                    f = service.files().create(body=meta, fields='id').execute()
                    folder_cache[year] = f['id']
                else:
                    folder_cache[year] = "DRY_RUN_ID"
        
        year_id = folder_cache[year]
        if dry_run: return "DRY_RUN_SUB_ID"

        # 2. Month Folder
        month_folder_name = f"{month_name}" # e.g. "01-January"
        cache_key = f"{year}/{month_folder_name}"
        
        if cache_key not in folder_cache:
             q = f"mimeType='application/vnd.google-apps.folder' and name='{month_folder_name}' and trashed=false and '{year_id}' in parents"
             res = service.files().list(q=q).execute()
             if res.get('files'):
                 folder_cache[cache_key] = res['files'][0]['id']
             else:
                 print(f"Creating folder: {year}/{month_folder_name}")
                 meta = {'name': month_folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [year_id]}
                 f = service.files().create(body=meta, fields='id').execute()
                 folder_cache[cache_key] = f['id']
                 
        return folder_cache[cache_key]

    import datetime
    
    print("Organizing files...")
    count = 0
    
    if dry_run:
        print("DRY RUN: Files will be moved to Year/Month folders.")
        print(f"Example: {files_to_move[0]['name']} -> {files_to_move[0]['createdTime'][:4]}")
    else:
        batch = service.new_batch_http_request()
        
        def callback(request_id, response, exception):
            if exception: print(f"Error moving {request_id}: {exception}")

        chunk_size = 50
        for i in range(0, len(files_to_move), chunk_size):
            chunk = files_to_move[i:i+chunk_size]
            batch = service.new_batch_http_request()
            
            for f in chunk:
                # Parse date
                dt_str = f.get('createdTime')
                if not dt_str: continue
                
                try:
                    dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    year = str(dt.year)
                    month_name = dt.strftime("%m-%B")
                    
                    target_folder_id = get_or_create_folder(year, month_name)
                    
                    # Move file: addParents=target, removeParents=current
                    prev_parents = ",".join(f.get('parents', []))
                    batch.add(service.files().update(fileId=f['id'], addParents=target_folder_id, removeParents=prev_parents), callback=callback)
                    
                except Exception as e:
                    print(f"Skipping {f['name']}: {e}")

            try:
                batch.execute()
                count += len(chunk)
                print(f"Moved {count}/{len(files_to_move)} files...", end='\r')
                time.sleep(1)
            except Exception as e:
                print(f"Batch error: {e}")
                
    print("\nOrganization Complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Organize Drive files.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    parser.add_argument('--confirm', action='store_true', help='Actually move files')
    args = parser.parse_args()
    
    organize_drive_files(args.profile, dry_run=not args.confirm)
