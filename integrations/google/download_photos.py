import os
import base64
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from .auth import get_credentials # Changed to relative import
import argparse
import datetime
import re

def clean_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def get_unique_filename(path):
    if not os.path.exists(path):
        return path
    filename, extension = os.path.splitext(path)
    counter = 1
    while os.path.exists(f"{filename}_{counter}{extension}"):
        counter += 1
    return f"{filename}_{counter}{extension}"

# Directory to save photos — configurable via DOWNLOAD_DIR env var
def download_photos(profile_name):
    _default_dir = os.path.expanduser(f"~/Downloads/OSP_Photos_{profile_name}")
    base_download_dir = os.getenv("DOWNLOAD_DIR", _default_dir)
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('gmail', 'v1', credentials=creds)

    query = 'has:attachment (filename:jpg OR filename:jpeg OR filename:png OR filename:gif OR filename:webp OR filename:heic)'
    
    print(f"Searching for emails with photos...")
    
    # Get all messages first
    messages = []
    next_page_token = None
    while True:
        results = service.users().messages().list(userId='me', q=query, pageToken=next_page_token).execute()
        messages.extend(results.get('messages', []))
        next_page_token = results.get('nextPageToken')
        if not next_page_token:
            break
            
    print(f"Found {len(messages)} emails. Starting download...")
    
    if not os.path.exists(base_download_dir):
        os.makedirs(base_download_dir)
        
    count = 0
    errors = 0

    for i, msg_meta in enumerate(messages):
        try:
            msg_id = msg_meta['id']
            msg = service.users().messages().get(userId='me', id=msg_id).execute()
            
            # Get date for sorting
            internal_date = int(msg['internalDate']) / 1000
            date_obj = datetime.datetime.fromtimestamp(internal_date)
            year = date_obj.strftime("%Y")
            month = date_obj.strftime("%m-%B") # 05-May
            
            # Create folder structure: Year/Month
            save_dir = os.path.join(base_download_dir, year, month)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            parts = msg.get('payload', {}).get('parts', [])
            
            # Function to process parts recursively
            def process_parts(parts):
                nonlocal count
                for part in parts:
                    if part.get('parts'):
                        process_parts(part['parts'])
                    
                    if part.get('filename') and part.get('body') and part.get('body').get('attachmentId'):
                        mime_type = part.get('mimeType', '').startswith('image/')
                        if mime_type:
                            att_id = part['body']['attachmentId']
                            filename = clean_filename(part['filename'])
                            if not filename:
                                filename = f"unnamed_image_{count}.jpg"
                                
                            att = service.users().messages().attachments().get(userId='me', messageId=msg_id, id=att_id).execute()
                            data = att['data']
                            file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                            
                            file_path = os.path.join(save_dir, filename)
                            final_path = get_unique_filename(file_path)
                            
                            with open(final_path, 'wb') as f:
                                f.write(file_data)
                            
                            count += 1
                            print(f"[{i+1}/{len(messages)}] Saved: {year}/{month}/{os.path.basename(final_path)}")

            process_parts(parts)
            
            # Also check top-level if not multipart
            if not parts and msg.get('payload').get('body').get('attachmentId'):
                 # Similar logic for non-multipart
                 part = msg['payload']
                 if part.get('mimeType', '').startswith('image/'):
                     # (Duplicate logic check would go here, but usually attachments imply multipart)
                     pass

        except Exception as e:
            print(f"Error processing message {msg_id}: {e}")
            errors += 1

    print(f"\nDownload complete!")
    print(f"Total photos downloaded: {count}")
    print(f"Errors encountered: {errors}")
    print(f"Files saved to: {base_download_dir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download photos from Gmail.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    args = parser.parse_args()
    
    download_photos(args.profile)
ч   