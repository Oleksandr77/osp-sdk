from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import asyncio
import logging

logger = logging.getLogger("uvicorn")

app = FastAPI()

from fastapi.responses import FileResponse

@app.get("/", response_class=FileResponse)
async def read_root():
    return FileResponse("static/index.html")

@app.get("/api/status")
async def get_status():
    return {"status": "online", "system": "AntiGravity Bot"}

@app.get("/api/chats")
async def get_chats():
    # In real integration, we'll fetch this from the bot instance
    return [
        {"id": 1, "name": "Business Ideas", "active": True},
        {"id": 2, "name": "Warsaw News", "active": True}
    ]

# Global variable to store public URL
public_url = None
ngrok_error = None

# Shared modules (populated by monitor_bot.py)
bot_modules = {
    "yt": None,
    "ai": None,
    "web": None
}

@app.get("/api/logs")
async def get_logs():
    return [{"time": "N/A", "msg": "Log feature pending"}]

@app.get("/api/search")
async def search_handler(
    q: str, 
    period: str = "any", 
    sort: str = "relevance", 
    limit: int = 10,
    source: str = "youtube"
):
    """Unified Search Handler (YouTube + Web Modes)."""
    
    if source == "youtube":
        if not bot_modules["yt"]:
            return {"error": "YouTube module not initialized"}
        
        # Map 'any' to None for the handler
        period_val = None if period == "any" else period
        
        results = await bot_modules["yt"].search_videos(
            query=q, 
            limit=limit, 
            period=period_val, 
            sort_by=sort
        )
        return results
        
    else:
        # Web / News / Reddit / Academic
        if not bot_modules["web"]:
            return {"error": "Web module not initialized"}
            
        # source can be: "google", "duckduckgo", "duckduckgo_news", "reddit", "academic"
        results = await bot_modules["web"].search_web(
            query=q,
            limit=limit,
            engine=source
        )
        return results

from pydantic import BaseModel

class PromptModel(BaseModel):
    id: str
    name: str
    icon: str
    text: str

@app.get("/api/analyzers")
async def get_analyzers():
    """Returns list of available AI prompt templates."""
    if not bot_modules["ai"]:
        return []
    
    # Convert dict to list for frontend
    analyzers = []
    for pid, data in bot_modules["ai"].prompts.items():
        analyzers.append({
            "id": pid,
            "name": data["name"],
            "icon": data["icon"]
        })
    return analyzers

@app.post("/api/analyzers")
async def create_analyzer(prompt: PromptModel):
    """Creates a new custom prompt."""
    if not bot_modules["ai"]:
        return {"error": "AI module not initialized"}
        
    success = bot_modules["ai"].save_prompt(
        p_id=prompt.id, 
        name=prompt.name, 
        icon=prompt.icon, 
        text=prompt.text
    )
    return {"success": success}

@app.get("/api/analyze")
async def analyze_handler(url: str, template: str = "general"):
    """Analyze video OR web page via unified handler."""
    if not bot_modules["ai"]:
        return {"error": "AI module not initialized"}
    
    # Check if YouTube
    is_youtube = any(x in url for x in ["youtube.com", "youtu.be"])
    
    if is_youtube:
        if not bot_modules["yt"]: return {"error": "YouTube module missing"}
        
        # 1. Get Video Info
        info = await bot_modules["yt"].analyze_video(url)
        if "error" in info: return info

        context = f"YouTube Video: {info['title']}"
        content_text = info.get("description", "")
        # In future: content_text += info.get("subtitles", "")
        
        title = info["title"]
        duration = info["duration"]
        thumbnail = info.get("thumbnail")
        
    else:
        # Web Analysis
        if not bot_modules["web"]: return {"error": "Web module missing"}
        
        # 1. Fetch Page
        info = await bot_modules["web"].fetch_page_content(url)
        if "error" in info: return info
        
        context = f"Web Page: {info['title']}"
        content_text = info.get("text", "")
        
        title = info["title"]
        duration = "Web Read"
        thumbnail = None

    # 2. Generate AI Summary
    summary = "AI Summary Unavailable"
    if bot_modules["ai"].is_active and content_text:
        summary = await bot_modules["ai"].summarize_text(
            text=content_text, 
            template_type=template,
            context=context
        )
        
        # 3. Save to Knowledge Base (Digital Brain)
        kb_data = {
            "title": title,
            "url": url,
            "author": info.get("author", "Unknown"),
            "source": "YouTube" if is_youtube else "Web",
            "summary": summary,
            "transcript": content_text, # Or full transcript if available
            "id": info.get("id", "") if is_youtube else "",
            "type": "video" if is_youtube else "article",
            "template": template
        }
        
        category = "YouTube" if is_youtube else "Web"
        saved_path = await bot_modules["ai"].save_to_knowledge_base(kb_data, category=category)
        logger.info(f"Analysis saved to KB: {saved_path}")
    
    return {
        "title": title,
        "duration": duration,
        "thumbnail": thumbnail,
        "summary": summary,
        "template_used": template
    }

# Function to run uvicorn in a way compatible with other asyncio loops
async def run_server():
    global public_url, ngrok_error
    
    # 1. Start ngrok tunnel
    try:
        import os as _os
        from pyngrok import ngrok
        # Auth token must be set via NGROK_AUTH_TOKEN env var (see .env.example)
        _ngrok_token = _os.getenv("NGROK_AUTH_TOKEN", "")
        if not _ngrok_token:
            raise RuntimeError("NGROK_AUTH_TOKEN environment variable is not set")
        ngrok.set_auth_token(_ngrok_token)
        
        # Open a HTTP tunnel on the default port 8000
        # <NgrokTunnel: "https://<public_sub>.ngrok-free.app" -> "http://localhost:8000">
        http_tunnel = ngrok.connect(8000)
        public_url = http_tunnel.public_url.replace("http://", "https://")
        logger.info(f"🚇 Ngrok Tunnel Started: {public_url}")
        ngrok_error = None
    except Exception as e:
        logger.error(f"Ngrok Error: {e}")
        ngrok_error = str(e)
        public_url = "http://127.0.0.1:8000"

    # 2. Start Uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_server())

@app.get("/api/kb_search")
async def search_kb(q: str):
    """Search the local Knowledge Base (Digital Brain)."""
    results = []
    
    # 1. Try Vector Search (Semantic)
    if "vector" in bot_modules and bot_modules["vector"]:
        try:
             vector_results = bot_modules["vector"].search(q, n_results=10)
             if vector_results:
                 # Format for frontend
                 for r in vector_results:
                     results.append({
                         "title": r['metadata'].get('title', 'Untitled'),
                         "path": r['metadata'].get('path', ''),
                         "category": r['metadata'].get('category', 'Unknown'),
                         "skill": r['metadata'].get('skill', ''),
                         "direction": r['metadata'].get('direction', ''),
                         "score": round(r['score'], 2),
                         "snippet": r['text'][:200] + "..."
                     })
                 return results
        except Exception as e:
             logger.error(f"Vector search failed: {e}")

    # 2. Fallback to Simple Index Search (Keyword)
    if not results and bot_modules["ai"]:
        return await bot_modules["ai"].search_knowledge_base(q)
        
    return results
