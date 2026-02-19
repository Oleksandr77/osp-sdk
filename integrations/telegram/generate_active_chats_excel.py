from telethon import TelegramClient
from datetime import datetime, timedelta, timezone
import pandas as pd
import asyncio

# Credentials
api_id = 13400748
api_hash = 'b8844f8c4a123fb138769432b214c13c'
session_name = 'antigravity_userbot'

client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.start()
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
    print(f"Searching for chats with activity since: {cutoff_date.date()}")
    
    active_chats = []
    
    # Iterate through all dialogs
    async for dialog in client.iter_dialogs():
        # Filter for Groups and Channels (and maybe private chats if user wants, request said "groups, channels, chats")
        # User said "groups, channels, chats", so we include all types including Users (Private)
        
        chat_type = "Unknown"
        if dialog.is_channel:
            chat_type = "Channel" if not dialog.is_group else "Group"
        elif dialog.is_group:
            chat_type = "Group"
        elif dialog.is_user:
            chat_type = "Private Chat"
            
        print(f"Checking {dialog.name} ({chat_type})...", end="\r")
        
        # Check if user sent a message in this chat in the last 90 days
        # We search for the most recent message from 'me'
        try:
            async for msg in client.iter_messages(dialog.id, from_user='me', limit=1):
                if msg.date and msg.date > cutoff_date:
                    active_chats.append({
                        "Chat Name": dialog.name,
                        "Chat ID": dialog.id,
                        "Type": chat_type,
                        "Last Activity": msg.date.strftime("%Y-%m-%d %H:%M"),
                        "Action / Keywords": "",
                        "Notification Method": ""
                    })
                break # We only need to know if there is AT LEAST one message
        except Exception as e:
            print(f"Skipping {dialog.name}: {e}")

    print(f"\nFound {len(active_chats)} active chats.")
    
    # Create DataFrame
    df = pd.DataFrame(active_chats)
    
    # Save to Excel
    output_file = "../../../10_Business_Admin/Telegram_Monitoring_Config.xlsx"
    df.to_excel(output_file, index=False)
    
    print(f"Saved to {output_file}")

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
