import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.metadata'
]

import argparse

def get_credentials(profile_name='default'):
    creds = None
    token_file = f'token_{profile_name}.json'
    
    # The file token_{profile_name}.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return creds

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Authenticate Google API with profiles.')
    parser.add_argument('--profile', type=str, default='default', help='Profile name for the account (e.g., "personal", "work")')
    args = parser.parse_args()

    print(f"Starting authentication check for profile: {args.profile}...")
    try:
        creds = get_credentials(args.profile)
        print(f"Authentication successful! Token saved to 'token_{args.profile}.json'.")
    except Exception as e:
        print(f"Authentication failed: {e}")
