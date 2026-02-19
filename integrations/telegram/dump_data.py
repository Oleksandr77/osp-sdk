from telethon import TelegramClient
from telethon.tl.types import InputMessagesFilterDocument
import csv
import os
import re
import asyncio

# Credentials — set via environment variables (see .env.example)
api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
api_hash = os.getenv("TELEGRAM_API_HASH", "")
session_name = 'osp_userbot'

# Output Paths — configurable via env vars
EXPORT_DIR = os.getenv("TELEGRAM_EXPORT_DIR", "./telegram_export")
DOCS_DIR = os.path.join(EXPORT_DIR, "Documents")
SECRETS_FILE = os.path.join(EXPORT_DIR, "Potential_Secrets.md")
CONTACTS_FILE = os.path.join(EXPORT_DIR, "Contacts.csv")
LINKS_FILE = os.path.join(EXPORT_DIR, "Saved_Links.md")

# Keywords for secrets searching
SECRET_KEYWORDS = [
    'password', 'pass', 'пароль', 'hasło', 'login', 'логин', 'api_key', 'secret',
    'credential', 'доступ', 'pin', 'code', 'auth', 'token', 'ключ'
]

client = TelegramClient(session_name, api_id, api_hash)

async def ensure_dirs():
    os.makedirs(DOCS_DIR, exist_ok=True)

from telethon.tl.functions.contacts import GetContactsRequest

async def export_contacts():
    print("Exporting Contacts...")
    # client.get_contacts() can be flaky or missing in some versions/mixins
    # Using raw API request
    result = await client(GetContactsRequest(hash=0))
    contacts = result.users
    
    with open(CONTACTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'First Name', 'Last Name', 'Phone', 'Username'])
        for user in contacts:
            writer.writerow([
                user.id, 
                user.first_name, 
                user.last_name, 
                getattr(user, 'phone', ''), 
                getattr(user, 'username', '')
            ])
    print(f"Saved {len(contacts)} contacts to {CONTACTS_FILE}")

async def analyze_saved_messages():
    print("Analyzing Saved Messages (me)...")
    
    secrets_found = []
    links_found = []
    files_downloaded = 0
    
    # Iterate through Saved Messages
    async for message in client.iter_messages('me'):
        text = message.message or ""
        
        # 1. Search for Secrets
        if text:
            lower_text = text.lower()
            if any(k in lower_text for k in SECRET_KEYWORDS):
                # Simple heuristic: ignore if it's too long (likely a forwarded article)
                # unless it has explicit "password:" structure
                if len(text) < 500 or "password" in lower_text or "пароль" in lower_text:
                    secrets_found.append({
                        'date': message.date,
                        'text': text
                    })

        # 2. Extract Links
        if text and ("http://" in text or "https://" in text):
            # Simple regex for links
            urls = re.findall(r'(https?://\S+)', text)
            for url in urls:
                links_found.append(f"- [{message.date.strftime('%Y-%m-%d')}] {url}")

        # 3. Download Documents (Files)
        if message.file:
            # Filter for documents/photos that look like useful files
            # (skip small thumbnails or stickers if possible, though message.file implies distinct media)
            
            # Determine filename
            file_name = None
            if message.document:
                for attr in message.document.attributes:
                    if hasattr(attr, 'file_name'):
                        file_name = attr.file_name
                        break
            
            if not file_name:
                # Generate a name based on date and type
                ext = message.file.ext or ".bin"
                file_name = f"file_{message.date.strftime('%Y%m%d_%H%M%S')}{ext}"
            
            save_path = os.path.join(DOCS_DIR, file_name)
            
            # Skip if exists
            if not os.path.exists(save_path):
                print(f"Downloading: {file_name}")
                await message.download_media(file=save_path)
                files_downloaded += 1

    # Save findings
    if secrets_found:
        with open(SECRETS_FILE, 'w', encoding='utf-8') as f:
            f.write("# Potential Secrets Strategy Found in Saved Messages\n\n")
            for item in secrets_found:
                f.write(f"### {item['date']}\n")
                f.write(f"```\n{item['text']}\n```\n\n")
        print(f"Found {len(secrets_found)} potential secrets.")

    if links_found:
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            f.write("# Links extracted from Saved Messages\n\n")
            f.write("\n".join(links_found))
        print(f"Found {len(links_found)} links.")

    print(f"Downloaded {files_downloaded} new files to {DOCS_DIR}")

async def main():
    await client.start()
    await ensure_dirs()
    await export_contacts()
    await analyze_saved_messages()
    print("\n✅ Telegram Dump Complete!")

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
