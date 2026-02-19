import os.path
import base64
import sys
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def _get_google_integrations_dir() -> str:
    """Return path to integrations/google dir via env var or source-tree fallback."""
    env_root = os.environ.get("OSP_INTEGRATIONS_ROOT")
    if env_root:
        return os.path.join(env_root, "google")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(current_dir, "..", "..", "..", "..", "..", "integrations", "google"))

def get_credentials(profile_name='default'):
    """Gets valid user credentials from local file."""
    google_integrations_dir = _get_google_integrations_dir()
    
    token_path = os.path.join(google_integrations_dir, f'token_{profile_name}.json')
    creds_path = os.path.join(google_integrations_dir, 'credentials.json')

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # We do NOT run implicit auth flow here as it requires browser interaction.
    # We assume tokens are present.
    return creds

def search_top_invoices(days=21, profile_name='default', limit=10):
    """
    Searches for invoices in the last N days.
    """
    creds = get_credentials(profile_name)
    if not creds:
        return f"Error: No credentials found for profile '{profile_name}'. Please run auth setup."

    try:
        service = build('gmail', 'v1', credentials=creds)
        
        # Calculate date
        date_after = (datetime.now() - timedelta(days=days)).strftime('%Y/%m/%d')
        
        # Build Query
        # "invoice OR bill OR receipt OR фактура OR rachunek"
        query_terms = "invoice OR bill OR receipt OR фактура OR rachunek OR payment"
        query = f'({query_terms}) after:{date_after}'
        
        print(f"Executing Gmail Search: {query}")
        
        results = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "No invoices found in the specified period."
            
        found_data = []
        for msg_meta in messages:
            msg = service.users().messages().get(userId='me', id=msg_meta['id']).execute()
            payload = msg['payload']
            headers = payload['headers']
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            
            # Create a direct link
            link = f"https://mail.google.com/mail/u/0/#inbox/{msg_meta['id']}"
            
            found_data.append({
                "date": date[:16], # Truncate time for readability
                "sender": sender,
                "subject": subject,
                "link": link
            })
            
        return found_data

    except Exception as e:
        return f"Gmail API Error: {str(e)}"
