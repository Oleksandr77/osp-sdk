from telethon import TelegramClient
import sys

# Credentials
api_id = 13400748
api_hash = 'b8844f8c4a123fb138769432b214c13c'
phone = '+48697138401'

session_name = 'antigravity_userbot'

print(f"Connecting as {phone}...")
client = TelegramClient(session_name, api_id, api_hash)

async def main():
    # Calling start(phone) initiates the login flow.
    # If authorized, it returns immediately.
    # If not, it sends code and prompts for input via stdin/stdout.
    await client.start(phone=phone)
    
    me = await client.get_me()
    print(f"Successfully logged in as {me.first_name} (ID: {me.id})")

if __name__ == '__main__':
    # We use client.loop manually to avoid the implicit start() from 'with client:'
    # causing issues if arguments aren't passed.
    client.loop.run_until_complete(main())
