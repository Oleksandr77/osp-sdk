from googleapiclient.discovery import build
from auth import get_credentials
import base64
from email.mime.text import MIMEText

import argparse

def get_service(profile_name='default'):
    creds = get_credentials(profile_name)
    service = build('gmail', 'v1', credentials=creds)
    return service

def list_unread_emails(profile_name='default', max_results=5):
    service = get_service(profile_name)
    results = service.users().messages().list(userId='me', q='is:unread', maxResults=max_results).execute()
    messages = results.get('messages', [])
    
    email_data = []
    if not messages:
        print(f'No unread messages found for profile "{profile_name}".')
    else:
        print(f'Unread messages for profile "{profile_name}":')
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            payload = msg['payload']
            headers = payload['headers']
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
            sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
            snippet = msg.get('snippet', '')
            
            email_data.append({
                'id': message['id'],
                'sender': sender,
                'subject': subject,
                'snippet': snippet
            })
            print(f"- From: {sender}, Subject: {subject}")
            
    return email_data

def send_email(to, subject, body, profile_name='default'):
    service = get_service(profile_name)
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        message = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        print(f'Message Id: {message["id"]} sent successfully.')
        return message
    except Exception as error:
        print(f'An error occurred: {error}')
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gmail Client with profiles.')
    parser.add_argument('--profile', type=str, default='default', help='Profile name for the account')
    args = parser.parse_args()
    
    # Test listing unread emails
    list_unread_emails(profile_name=args.profile)
