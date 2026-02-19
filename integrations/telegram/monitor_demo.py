from telethon import TelegramClient, events
import sys
import os

# Credentials — set via environment variables (see .env.example)
api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
api_hash = os.getenv("TELEGRAM_API_HASH", "")
session_name = 'osp_userbot'

# Keywords to watch for (case-insensitive)
KEYWORDS = ['терміново', 'оплата', 'договір', 'звіт', 'важливо', 'urgent', 'invoice']

# Chats to monitor (can be ID or username). Empty list = ALL chats.
# SOURCE_CHATS = [-100123456789, 'username'] 
SOURCE_CHATS = [] 

client = TelegramClient(session_name, api_id, api_hash)

@client.on(events.NewMessage(chats=SOURCE_CHATS if SOURCE_CHATS else None))
async def handler(event):
    # Ignore your own messages
    if event.out:
        return

    text = event.message.message or ""
    
    # Check for keywords
    for keyword in KEYWORDS:
        if keyword.lower() in text.lower():
            sender = await event.get_sender()
            sender_name = getattr(sender, 'first_name', 'Unknown')
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', 'Private Chat')

            print(f"🔔 ALERT: Keyword '{keyword}' found!")
            print(f"   From: {sender_name}")
            print(f"   Chat: {chat_title}")
            print(f"   Message: {text[:100]}...")
            print("-" * 40)
            
            # Here we could:
            # - Send a message to "Saved Messages"
            # - Send an email
            # - Add a task to Trello/Notion
            # - Play a sound
            
            # For demo, just forward to Saved Messages
            await event.message.forward_to('me')
            break

print("Monitoring started... Press Ctrl+C to stop.")
print(f"Watching for keywords: {', '.join(KEYWORDS)}")

if __name__ == '__main__':
    with client:
        client.run_until_disconnected()
