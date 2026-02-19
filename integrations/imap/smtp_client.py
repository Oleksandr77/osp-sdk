import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json

class SMTPClient:
    def __init__(self, config_path='email_config.json', profile='default'):
        self.profile = profile
        self.config = self._load_config(config_path)

    def _load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file {path} not found.")
        with open(path, 'r') as f:
            config = json.load(f)
        
        if self.profile not in config:
            raise ValueError(f"Profile '{self.profile}' not found in configuration.")
        
        return config[self.profile]

    def send_email(self, to_email, subject, body):
        host = self.config.get('smtp_server')
        port = self.config.get('smtp_port', 587)
        user = self.config.get('email')
        password = self.config.get('password')

        if not all([host, user, password]):
            raise ValueError("Missing SMTP configuration (server, email, or password).")

        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(host, port)
            server.starttls()
            server.login(user, password)
            text = msg.as_string()
            server.sendmail(user, to_email, text)
            server.quit()
            print(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='SMTP Client')
    parser.add_argument('--profile', type=str, default='default', help='Profile name')
    parser.add_argument('--config', type=str, default='email_config.json', help='Config file path')
    parser.add_argument('--to', type=str, required=True, help='Recipient email')
    parser.add_argument('--subject', type=str, default='Test Subject', help='Email subject')
    parser.add_argument('--body', type=str, default='Test Body', help='Email body')
    args = parser.parse_args()

    client = SMTPClient(config_path=args.config, profile=args.profile)
    client.send_email(args.to, args.subject, args.body)
