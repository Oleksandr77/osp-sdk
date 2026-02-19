#!/bin/bash
cd "$(dirname "$0")"

# Ensure venv exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Cleanup old processes
pkill -f monitor_bot.py || true
pkill -f ngrok || true

source venv/bin/activate

# Install requirements if not present (simple check)
pip install -q fastapi uvicorn pyngrok jinja2 telethon yt-dlp google-generativeai pandas openpyxl textblob googlesearch-python beautifulsoup4 requests duckduckgo-search

export GEMINI_API_KEY="AIzaSyDvtQfuVN9X6ltN5z1rFLLrJ8uoJHa-QHc" # Replace with your key

# Run the unified bot + server
python3 monitor_bot.py
