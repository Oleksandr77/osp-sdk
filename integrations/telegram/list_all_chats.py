from telethon import TelegramClient
import csv
import sys
import os

# Credentials — set via environment variables (see .env.example)
api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
api_hash = os.getenv("TELEGRAM_API_HASH", "")
session_name = 'osp_userbot'

client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.start()
    
    dialogs = await client.get_dialogs()
    
    print(f"{'ID':<15} | {'Type':<10} | {'Name'}")
    print("-" * 60)
    
    groups = []
    channels = []
    
    for d in dialogs:
        if d.is_group:
            groups.append(d)
        elif d.is_channel:
            # Channels that are not groups (megagroups are handled in is_group usually, but Telethon distinguishes)
            channels.append(d)
            
    print("\n--- 📢 CHANNELS ---")
    for d in channels:
        print(f"{d.id:<15} | Channel    | {d.name}")

    print("\n--- 👥 GROUPS ---")
    for d in groups:
        print(f"{d.id:<15} | Group      | {d.name}")

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
