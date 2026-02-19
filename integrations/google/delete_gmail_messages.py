from googleapiclient.discovery import build
from auth import get_credentials
import argparse
import time
import random
from googleapiclient.errors import HttpError

def delete_gmail_messages(profile_name, query, dry_run=True):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('gmail', 'v1', credentials=creds)

    print(f"Target Query: {query}")
    
    # 1. Find Messages
    messages = []
    page_token = None
    
    def safe_execute(request):
        max_retries = 5
        for n in range(max_retries):
            try:
                return request.execute()
            except HttpError as error:
                if error.resp.status in [403, 429]:
                    time.sleep((2 ** n) + random.random())
                else: raise
        return request.execute()

    print("Searching for messages...")
    while True:
        results = safe_execute(service.users().messages().list(userId='me', q=query, pageToken=page_token))
        batch_msgs = results.get('messages', [])
        messages.extend(batch_msgs)
        page_token = results.get('nextPageToken')
        print(f"Found {len(messages)} messages...", end='\r')
        if not page_token:
            break
            
    print(f"\nTotal messages matching query: {len(messages)}")
    
    if len(messages) == 0:
        return

    if dry_run:
        print("\nDRY RUN: No messages were deleted.")
        print("Use --confirm to actually delete messages.")
    else:
        print("\nDELETING MESSAGES...")
        # batchDelete supports up to 1000 IDs
        batch_ids = [msg['id'] for msg in messages]
        
        count = 0
        chunk_size = 1000
        for i in range(0, len(batch_ids), chunk_size):
            chunk = batch_ids[i:i+chunk_size]
            try:
                safe_execute(service.users().messages().batchDelete(userId='me', body={'ids': chunk}))
                count += len(chunk)
                print(f"Deleted {count}/{len(batch_ids)} messages...", end='\r')
                time.sleep(1)
            except Exception as e:
                print(f"\nError deleting batch: {e}")
                
        print("\nDeletion Complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Delete Gmail messages.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    parser.add_argument('--query', type=str, required=True, help='Gmail search query')
    parser.add_argument('--confirm', action='store_true', help='Actually delete messages')
    args = parser.parse_args()
    
    delete_gmail_messages(args.profile, args.query, dry_run=not args.confirm)
