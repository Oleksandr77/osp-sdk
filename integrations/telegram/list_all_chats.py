from telethon import TelegramClient
import csv
import sys

# Credentials (reusing from connect_telegram.py)
api_id = 13400748
api_hash = 'b8844f8c4a123fb138769432b214c13c'
session_name = 'antigravity_userbot'

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
