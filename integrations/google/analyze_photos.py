from googleapiclient.discovery import build
from auth import get_credentials
import argparse

def analyze_photos(profile_name):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('gmail', 'v1', credentials=creds)

    # Query for messages with image attachments
    # We look for common image extensions
    query = 'has:attachment (filename:jpg OR filename:jpeg OR filename:png OR filename:gif OR filename:webp OR filename:heic)'
    
    print(f"Searching for emails with photos using query: '{query}'")
    print("This might take a moment if there are many emails...")

    total_messages = 0
    total_attachments = 0
    
    # Pagination
    next_page_token = None
    messages = []
    
    while True:
        results = service.users().messages().list(userId='me', q=query, pageToken=next_page_token).execute()
        batch = results.get('messages', [])
        messages.extend(batch)
        
        # Limit to avoid hitting limits or taking too long for a quick check
        # Let's start with just counting messages first for speed
        
        next_page_token = results.get('nextPageToken')
        if not next_page_token:
            break

    print(f"\nFound {len(messages)} emails that match the photo search criteria.")
    print("Analyzing attachment details for the first 50 emails to give a statistically significant sample...")

    # Analyze a subset to count actual attachments (messages can have multiple)
    sample_size = min(len(messages), 50)
    for msg_meta in messages[:sample_size]:
        msg_id = msg_meta['id']
        msg_detail = service.users().messages().get(userId='me', id=msg_id).execute()
        
        parts = msg_detail.get('payload', {}).get('parts', [])
        
        # Helper to find attachments in nested parts
        def count_images_in_parts(parts):
            count = 0
            for part in parts:
                if part.get('filename') and part.get('mimeType', '').startswith('image/'):
                    count += 1
                if part.get('parts'):
                    count += count_images_in_parts(part['parts'])
            return count

        img_count = count_images_in_parts(parts)
        # If parts list is empty but it's a direct attachment (less common in multipart/mixed)
        # We can also check filename in payload
        if not parts and msg_detail.get('payload', {}).get('filename'):
             if msg_detail['payload']['mimeType'].startswith('image/'):
                 img_count = 1

        total_attachments += img_count

    # Extrapolate if we only checked a sample
    estimated_total = total_attachments
    if len(messages) > sample_size:
        avg_per_email = total_attachments / sample_size
        estimated_total = int(avg_per_email * len(messages))
        print(f"\nBased on a sample of {sample_size} emails, we found {total_attachments} photo attachments.")
        print(f"Estimated total photo attachments in all {len(messages)} emails: ~{estimated_total}")
    else:
        print(f"\nTotal photo attachments found: {total_attachments}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze photos in Gmail.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    args = parser.parse_args()
    
    analyze_photos(args.profile)
