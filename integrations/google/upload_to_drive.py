from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from auth import get_credentials
import argparse
import os
import time
from googleapiclient.errors import HttpError

def upload_folder_to_drive(profile_name, local_folder, drive_folder_name, parent_id=None):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('drive', 'v3', credentials=creds) # Use v3 for fields/queries

    # 1. Get or Create Target Root Folder
    def get_or_create_folder(name, parent=None):
        q = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false"
        if parent:
            q += f" and '{parent}' in parents"
        else:
            q += " and 'root' in parents"
            
        res = service.files().list(q=q, fields='files(id)').execute()
        files = res.get('files', [])
        
        if files:
            return files[0]['id']
        else:
            print(f"Creating folder: {name}")
            meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
            if parent:
                meta['parents'] = [parent]
            
            f = service.files().create(body=meta, fields='id').execute()
            return f['id']

    target_root_id = get_or_create_folder(drive_folder_name, parent_id)
    print(f"Target Drive Folder: {drive_folder_name} ({target_root_id})")

    # 2. Recursive Upload
    def upload_recursive(local_path, parent_drive_id):
        items = os.listdir(local_path)
        items.sort()
        
        for item in items:
            item_path = os.path.join(local_path, item)
            
            # Helper to check if file already exists
            def file_exists(name, parent):
                q = f"name='{name}' and '{parent}' in parents and trashed=false"
                res = service.files().list(q=q, fields='files(id, size)').execute()
                return res.get('files', [])

            if os.path.isdir(item_path):
                # Handle Directory
                # Check if exists first
                folder_id = get_or_create_folder(item, parent_drive_id)
                upload_recursive(item_path, folder_id)
                
            else:
                # Handle File
                if item.startswith('.'): continue # Skip hidden files
                
                existing = file_exists(item, parent_drive_id)
                if existing:
                    # Simple check: skip if exists (assuming same file)
                    # print(f"Skipping {item} (already exists)")
                    continue
                
                print(f"Uploading {item}...", end='\r')
                
                # Retry logic for upload
                for retry in range(3):
                    try:
                        file_metadata = {'name': item, 'parents': [parent_drive_id]}
                        media = MediaFileUpload(item_path, resumable=True)
                        f = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                        break
                    except Exception as e:
                        print(f"\nError uploading {item}: {e}")
                        time.sleep(2)

    print(f"Starting upload from {local_folder}...")
    upload_recursive(local_folder, target_root_id)
    print("\nUpload Complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload folder to Drive.')
    parser.add_argument('--profile', type=str, required=True, help='Target Drive Profile (e.g. MSYSTEM017)')
    parser.add_argument('--source', type=str, required=True, help='Local source folder path')
    parser.add_argument('--dest', type=str, required=True, help='Destination folder name on Drive')
    args = parser.parse_args()
    
    upload_folder_to_drive(args.profile, args.source, args.dest)
