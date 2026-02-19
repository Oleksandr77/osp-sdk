import os
import requests
from typing import Dict, Any

# Environment extraction
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a message via Telegram Bot API.
    Arguments:
      - chat_id: The target chat ID.
      - text: The message content.
      - parse_mode: Optional (Markdown, HTML).
    """
    chat_id = arguments.get("chat_id")
    text = arguments.get("text")
    parse_mode = arguments.get("parse_mode", "Markdown")

    if not chat_id or not text:
        return {"error": "Missing 'chat_id' or 'text'."}

    # If running inside monitor_bot.py context, we might prefer using the client directly.
    # But for a standard skill, we use HTTP API.
    
    if not BOT_TOKEN:
         return {"error": "TELEGRAM_BOT_TOKEN not configured."}

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if not data.get("ok"):
            return {"error": f"Telegram API Error: {data.get('description')}"}
            
        return {
            "status": "success",
            "message_id": data["result"]["message_id"]
        }
    except Exception as e:
        return {"error": f"Failed to send message: {str(e)}"}
