from googleapiclient.discovery import build
from auth import get_credentials
import argparse
import time
import random
from googleapiclient.errors import HttpError

def safe_execute(request):
    max_retries = 10
    for n in range(max_retries):
        try:
            return request.execute()
        except HttpError as error:
            if error.resp.status in [403, 429]:
                if n == max_retries - 1: raise
                sleep_time = (2 ** n) + random.random()
                print(f"Rate limited. Sleeping {sleep_time:.2f}s...", end='\r')
                time.sleep(sleep_time)
            elif error.resp.status == 500:
                time.sleep(1)
            else:
                raise
    return request.execute()

def analyze_email_storage(profile_name):
    print(f"Authenticating as {profile_name}...")
    creds = get_credentials(profile_name)
    service = build('gmail', 'v1', credentials=creds)

    def sizeof_fmt(num, suffix="B"):
        for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
            if abs(num) < 1024.0:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.1f}Pi{suffix}"

    print(f"Analyzing Gmail storage usage for {profile_name}...")
    
    def get_query_size(query):
        total_size = 0
        count = 0
        page_token = None
        while True:
            try:
                results = safe_execute(service.users().messages().list(userId='me', q=query, pageToken=page_token))
            except Exception as e:
                print(f"\nError listing messages: {e}")
                break

            messages = results.get('messages', [])
            
            if not messages:
                break
            
            # Batch request with rate limiting
            # Limit batch size to avoid hitting limits
            # Google Batch limit is 1000, but rate limit is queries/second
            
            batch_sizes = []
            def callback(request_id, response, exception):
                if response:
                    batch_sizes.append(response.get('sizeEstimate', 0))
                elif exception:
                    pass

            # Process in smaller chunks to avoid hitting limits
            chunk_size = 50 
            for i in range(0, len(messages), chunk_size):
                chunk = messages[i:i+chunk_size]
                batch = service.new_batch_http_request()
                for msg in chunk:
                    batch.add(service.users().messages().get(userId='me', id=msg['id'], fields='sizeEstimate'), callback=callback)
                
                try:
                    safe_execute(batch)
                    # Respectful sleep between chunks
                    time.sleep(1) 
                except Exception as e:
                    print(f"\nBatch execution error: {e}")
                    time.sleep(5)
            
            total_size += sum(batch_sizes)
            count += len(messages)
            
            print(f"Scanned {count} emails...", end='\r')
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        return count, total_size

    # 1. Size of Photo Emails (since we already downloaded them)
    print("\n1. Calculating size of emails with images (which we backed up)...")
    query_photos = 'has:attachment (filename:jpg OR filename:jpeg OR filename:png OR filename:gif OR filename:webp OR filename:heic)'
    photo_count, photo_size = get_query_size(query_photos)
    print(f"\n   - Count: {photo_count}")
    print(f"   - Total Size: {sizeof_fmt(photo_size)}")

    # 2. Large files (Video/Other)
    print("\n2. Scanning for really large emails (>10MB)...")
    large_count, large_size = get_query_size('size:10485760') # 10MB bytes
    print(f"\n   - Count: {large_count}")
    print(f"   - Total Size: {sizeof_fmt(large_size)}")
    
    # 3. Old emails
    # print("\n3. Scanning old emails (older than 5 years)...")
    # old_count, old_size = get_query_size('older_than:5y')
    # print(f"\n   - Count: {old_count}")
    # print(f"   - Total Size: {sizeof_fmt(old_size)}")

    print("\n" + "="*40)
    print("GMAIL STORAGE SUMMARY")
    print("="*40)
    print(f"Potential Savings:")
    print(f"[ ] Delete Photo-Emails (Backed up): {sizeof_fmt(photo_size)}")
    print(f"[ ] Delete Large Emails (>10MB):     {sizeof_fmt(large_size)}")
    # print(f"[ ] Delete Old Emails (>5 years):    {sizeof_fmt(old_size)}")
    print("="*40)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze Gmail storage.')
    parser.add_argument('--profile', type=str, required=True, help='Profile name')
    args = parser.parse_args()
    
    analyze_email_storage(args.profile)
