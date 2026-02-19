import imaplib
import email
from email.header import decode_header
import datetime
import os
import json

class IMAPClient:
    def __init__(self, config_path='email_config.json', profile='default'):
        self.profile = profile
        self.config = self._load_config(config_path)
        self.connection = None

    def _load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file {path} not found.")
        with open(path, 'r') as f:
            config = json.load(f)
        
        if self.profile not in config:
            raise ValueError(f"Profile '{self.profile}' not found in configuration.")
        
        return config[self.profile]

    def connect(self):
        host = self.config.get('imap_server')
        port = self.config.get('imap_port', 993)
        user = self.config.get('email')
        password = self.config.get('password')

        if not all([host, user, password]):
            raise ValueError("Missing IMAP configuration (server, email, or password).")

        try:
            self.connection = imaplib.IMAP4_SSL(host, port)
            self.connection.login(user, password)
            print(f"Connected to {host} as {user}")
        except Exception as e:
            print(f"Failed to connect via IMAP: {e}")
            raise

    def list_unread_emails(self, max_results=5):
        if not self.connection:
            self.connect()

        self.connection.select("INBOX")
        status, messages = self.connection.search(None, "UNSEEN")
        
        if status != "OK":
            print("No unread messages found or error searching.")
            return []

        email_ids = messages[0].split()
        # Fetch latest first
        email_ids = email_ids[-max_results:] if email_ids else []
        
        email_data = []

        if not email_ids:
             print(f'No unread messages found for profile "{self.profile}".')
             return []

        print(f'Unread messages for profile "{self.profile}":')

        for e_id in reversed(email_ids):
            _, msg_data = self.connection.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    from_ = msg.get("From")
                    
                    # Extract plain text body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            try:
                                body = part.get_payload(decode=True).decode()
                            except:
                                pass
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    snippet = body[:100].replace('\n', ' ') if body else ""

                    email_data.append({
                        'id': e_id.decode(),
                        'sender': from_,
                        'subject': subject,
                        'snippet': snippet
                    })
                    print(f"- From: {from_}, Subject: {subject}")

        return email_data

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection.logout()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='IMAP Client')
    parser.add_argument('--profile', type=str, default='default', help='Profile name')
    parser.add_argument('--config', type=str, default='email_config.json', help='Config file path')
    args = parser.parse_args()

    try:
        client = IMAPClient(config_path=args.config, profile=args.profile)
        client.list_unread_emails()
        client.close()
    except Exception as e:
        print(f"Error: {e}")
