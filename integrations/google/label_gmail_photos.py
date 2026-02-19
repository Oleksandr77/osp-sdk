from googleapiclient.discovery import build
from auth import get_credentials
import argparse
import time
import random
from googleapiclient.errors import HttpError

def label_gmail_photos(profile_name, dry_run=True):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('gmail', 'v1', credentials=creds)

    label_name = "Antigravity_Photos"
    print(f"Searching for photo-emails to label as '{label_name}'...")
    
    query = 'has:attachment (filename:jpg OR filename:jpeg OR filename:png OR filename:gif OR filename:webp OR filename:heic) -label:Antigravity_Photos'
    
    # 1. Get/Create Label
    label_id = None
    if not dry_run:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        for l in labels:
            if l['name'] == label_name:
                label_id = l['id']
                break
        
        if not label_id:
            print(f"Creating label: {label_name}")
            created = service.users().labels().create(userId='me', body={'name': label_name}).execute()
            label_id = created['id']
    else:
        print(f"DRY RUN: Would create label '{label_name}'")

    # 2. Find Messages
    messages = []
    page_token = None
    
    while True:
        try:
            results = service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
            batch_msgs = results.get('messages', [])
            messages.extend(batch_msgs)
            page_token = results.get('nextPageToken')
            print(f"Found {len(messages)} messages to label...", end='\r')
            if not page_token: break
        except Exception as e:
            print(f"Error scanning: {e}")
            break
            
    print(f"\nFound {len(messages)} messages without the label.")
    
    if len(messages) == 0:
        return

    if dry_run:
        print("DRY RUN: Skipped labeling.")
        print("Use --confirm to apply labels.")
    else:
        print(f"Applying label {label_name} ({label_id})...")
        
        batch_ids = [msg['id'] for msg in messages]
        chunk_size = 1000
        count = 0
        
        for i in range(0, len(batch_ids), chunk_size):
            chunk = batch_ids[i:i+chunk_size]
            body = {'ids': chunk, 'addLabelIds': [label_id]}
            try:
                service.users().messages().batchModify(userId='me', body=body).execute()
                count += len(chunk)
                print(f"Labeled {count}/{len(batch_ids)} messages...", end='\r')
                time.sleep(1)
            except Exception as e:
                print(f"Error labeling batch: {e}")
                time.sleep(2)
                
        print("\nLabeling Complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Label Gmail photos.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    parser.add_argument('--confirm', action='store_true', help='Actually apply labels')
    args = parser.parse_args()
    
    label_gmail_photos(args.profile, dry_run=not args.confirm)
