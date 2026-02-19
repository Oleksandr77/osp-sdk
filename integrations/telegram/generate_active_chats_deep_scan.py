from telethon import TelegramClient
from datetime import datetime, timedelta, timezone
import pandas as pd
import asyncio
import os

# Credentials — set via environment variables (see .env.example)
api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
api_hash = os.getenv("TELEGRAM_API_HASH", "")
session_name = 'osp_userbot'

client = TelegramClient(session_name, api_id, api_hash)

TARGET_NAMES = ["Prezes", "Мєтт", "Nosatskyi", "Виктория", "Ірина", "Kostya"]

async def main():
    await client.start()
    
    me = await client.get_me()
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
    print(f"Searching for chats with activity since: {cutoff_date.date()}")
    
    active_chats = []
    
    # Iterate through ALL dialogs (ignore date order to be safe)
    async for dialog in client.iter_dialogs(limit=None):
        
        chat_type = "Unknown"
        if dialog.is_channel:
            chat_type = "Channel" if not dialog.is_group else "Group"
        elif dialog.is_group:
            chat_type = "Group"
        elif dialog.is_user:
            chat_type = "Private Chat"
            
        print(f"Checking {dialog.name}...", end="\r")
        
        # Debug for specific missing names
        for target in TARGET_NAMES:
            if target.lower() in dialog.name.lower():
                print(f"\n[DEBUG] Found target chat: {dialog.name} (ID: {dialog.id})")
        
        is_active = False
        last_msg_date = None
        
        # Method 1: Check if dialog.date is recent (last message in chat)
        # If the CHAT hasn't had activity in 90 days, we can skip deeper scan
        if dialog.date and dialog.date < cutoff_date:
            continue

        # Method 2: Scan last 100 messages for MY messages
        try:
            async for msg in client.iter_messages(dialog.id, from_user='me', limit=100):
                if msg.date and msg.date > cutoff_date:
                    is_active = True
                    last_msg_date = msg.date
                    # Found one, that's enough to mark as active
                    break 
        except Exception as e:
            pass

        if is_active:
             active_chats.append({
                "Chat Name": dialog.name,
                "Chat ID": dialog.id,
                "Type": chat_type,
                "Last Activity": last_msg_date.strftime("%Y-%m-%d %H:%M") if last_msg_date else "Recent",
                "Action (Keywords/Files/Forward)": "",
                "Notification Method (Email/Saved Messages)": "",
                "Frequency": "Real-time"
            })

    print(f"\nFound {len(active_chats)} active chats.")
    
    # Summary of types
    if active_chats:
        type_counts = pd.DataFrame(active_chats)["Type"].value_counts()
        print("\nBreakdown:")
        print(type_counts)
    
    # Create DataFrame
    df = pd.DataFrame(active_chats)
    
    # Save to Excel
    output_file = os.getenv("TELEGRAM_MONITORING_OUTPUT", "./Telegram_Monitoring_Config.xlsx")
    df.to_excel(output_file, index=False)
    
    print(f"Saved to {output_file}")

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
