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
    
    me = await client.get_me()
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
    print(f"Searching for chats with activity since: {cutoff_date.date()}")
    
    active_chats = []
    
    # Iterate through dialogs (default order is by last message date)
    async for dialog in client.iter_dialogs():
        # Optimization: If the chat's last message is older than cutoff, 
        # then certainly I haven't sent anything new either.
        # Dialogs are ordered by date, so we can stop completely once we hit old chats.
        if dialog.date and dialog.date < cutoff_date:
            print(f"Reached old dialogs ({dialog.date}). Stopping search.")
            break
            
        chat_type = "Unknown"
        if dialog.is_channel:
            chat_type = "Channel" if not dialog.is_group else "Group"
        elif dialog.is_group:
            chat_type = "Group"
        elif dialog.is_user:
            chat_type = "Private Chat"
            
        print(f"Checking {dialog.name} ({chat_type})...", end="\r")
        
        is_active = False
        last_msg_date = None
        
        # Check if the last message in dialog is from me
        if dialog.message and dialog.message.sender_id == me.id:
            is_active = True
            last_msg_date = dialog.message.date
        else:
            # If not, scan recent history for my messages
            # We ONLY scan if the chat itself has been active recently (which is guaranteed by the loop check above)
            try:
                async for msg in client.iter_messages(dialog.id, from_user='me', limit=1):
                    if msg.date and msg.date > cutoff_date:
                        is_active = True
                        last_msg_date = msg.date
                    break 
            except Exception as e:
                # Some channels might forbid reading messages or other errors
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
    type_counts = pd.DataFrame(active_chats)["Type"].value_counts()
    print("\nBreakdown:")
    print(type_counts)

    # Create DataFrame
    df = pd.DataFrame(active_chats)

    
    # Save to Excel
    output_file = "../../../10_Business_Admin/Telegram_Monitoring_Config.xlsx"
    df.to_excel(output_file, index=False)
    
    print(f"Saved to {output_file}")

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
