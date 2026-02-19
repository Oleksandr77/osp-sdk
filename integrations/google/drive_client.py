from googleapiclient.discovery import build
from auth import get_credentials

import argparse

def get_service(profile_name='default'):
    creds = get_credentials(profile_name)
    service = build('drive', 'v3', credentials=creds)
    return service

def list_recent_files(profile_name='default', page_size=10):
    service = get_service(profile_name)
    results = service.files().list(
        pageSize=page_size, fields="nextPageToken, files(id, name, mimeType)").execute()
    items = results.get('files', [])

    if not items:
        print(f'No files found for profile "{profile_name}".')
    else:
        print(f'Files for profile "{profile_name}":')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))
    return items

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Drive Client with profiles.')
    parser.add_argument('--profile', type=str, default='default', help='Profile name for the account')
    args = parser.parse_args()

    list_recent_files(profile_name=args.profile)
