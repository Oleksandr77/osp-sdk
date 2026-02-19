from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel
from datetime import datetime, timedelta, timezone
import sys

# Credentials (reusing from connect_telegram.py)
api_id = 13400748
api_hash = 'b8844f8c4a123fb138769432b214c13c'
session_name = 'antigravity_userbot'

client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.connect()
    if not await client.is_user_authorized():
        print("Error: Not authorized. Please run connect_telegram.py first.")
        return

    # 3 months ago (UTC)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
    
    print(f"Scanning for chats active since: {cutoff_date.strftime('%Y-%m-%d')}\n")
    print(f"{'Type':<10} | {'Name':<50} | {'Last Date'}")
    print("-" * 80)

    # Fetch dialogs (limit to recent ones to save time, but check date)
    # dialogs are returned in reverse chronological order (newest first).
    # so we can stop once we hit a dialog older than cutoff_date? 
    # Not necessarily, because pinned chats might be at top but old.
    # But usually dialogs Iteration yields based on last message date.
    
    count = 0
    async for dialog in client.iter_dialogs(limit=None):
        date = dialog.date
        if not date:
            continue
            
        # Ensure date is timezone-aware for comparison
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
            
        if date < cutoff_date:
            # If standard dialog sorting (by date) holds, we *could* break here.
            # But pinned chats break this order. So we just skip older ones.
            # For strict correctness we should iterate enough.
            # To be safe against massive history, let's just loop.
            # However, if we see *many* consecutive old chats (unpinned), we can probably stop.
            continue

        entity = dialog.entity
        name = dialog.name or "Unknown"
        # Determine type
        chat_type = "Unknown"
        if isinstance(entity, User):
            chat_type = "User"
            if entity.bot:
                chat_type = "Bot"
        elif isinstance(entity, Chat):
            chat_type = "Group"
        elif isinstance(entity, Channel):
            if entity.megagroup:
                chat_type = "Supergroup"
            else:
                chat_type = "Channel"

        # Sanitize name for printing
        safe_name = name.replace('\n', ' ').strip()[:45]
        
        print(f"{chat_type:<10} | {safe_name:<50} | {date.strftime('%Y-%m-%d')}")
        count += 1
        
    print("-" * 80)
    print(f"Total found: {count}")

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
