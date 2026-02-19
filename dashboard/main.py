import os
import sys
import logging
from typing import List, Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add operations root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_core.agent_manager import AgentManager
from ai_core.skill_manager import SkillManager
from ai_core.vector_handler import VectorHandler

# Configure Structured JSON Logging (matches server.py)
try:
    from osp_server.logic.json_logger import configure_json_logging
    configure_json_logging()
except ImportError:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OSP Agent Dashboard")

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
templates = Jinja2Templates(directory=templates_dir)

# Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount OSP Server (Protocol endpoints: /health, /osp-rpc, /metrics, /admin/*)
try:
    from osp_server.server import app as osp_app
    app.mount("/osp", osp_app)
    logger.info("✅ OSP Server mounted at /osp (endpoints: /osp/health, /osp/osp-rpc, /osp/metrics)")
except Exception as e:
    logger.warning(f"⚠️ Failed to mount OSP Server: {e}")


# Initialize OSP System (Singleton-ish)
class OSPSystem:
    def __init__(self):
        self.skill_manager = SkillManager()
        self.vector_handler = VectorHandler()
        self.agent_manager = AgentManager(self.skill_manager, vector_db=self.vector_handler)
        self.session = self.agent_manager.create_session({
            "name": "Web Assistant",
            "role": "assistant",
            "system_prompt": "You are a helpful AI assistant accessible via a Web Dashboard."
        })
        logger.info(f"OSP System Initialized. Session ID: {self.session.session_id}")

system = OSPSystem()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "session_id": system.session.session_id,
        "skills": system.skill_manager.skills
    })

@app.get("/chat", response_class=HTMLResponse)
async def chat_ui(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request, "session_id": system.session.session_id})

@app.post("/api/chat")
async def chat_api(message: str = Form(""), session_id: str = Form(...), image: Optional[str] = Form(None)):
    if not message and not image:
        return {"error": "Empty message"}
    
    logger.info(f"Web Chat Message: '{message}' Image: {'Yes' if image else 'No'}")
    result = system.agent_manager.execute_agent(session_id, message, image_data=image)
    
    return {
        "user_message": message,
        "image_uploaded": bool(image),
        "agent_response": result.get("result", {}).get("message") or result.get("result", {}).get("summary") or str(result),
        "rag_context_used": "RELEVANT KNOWLEDGE FROM MEMORY" in str(result.get("message", "")) and not image
    }

# --- Skill Builder ---
from typing import Dict, Any
from pydantic import BaseModel

class SkillCreateRequest(BaseModel):
    name: str
    description: str
    instructions: str
    parameters: Dict[str, Any]

@app.get("/builder", response_class=HTMLResponse)
async def builder_ui(request: Request):
    return templates.TemplateResponse("builder.html", {"request": request, "session_id": system.session.session_id})

@app.post("/api/skills/create")
async def create_skill_endpoint(skill: SkillCreateRequest):
    import yaml
    
    # Define paths
    skill_id = skill.name
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../skills/user", skill_id))
    
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        
    # 1. Create metadata.yaml
    metadata = {
        "name": skill.name,
        "description": skill.description,
        "id": f"user.{skill_id}",
        "parameters": {
             "type": "object",
             "properties": skill.parameters,
             "required": list(skill.parameters.keys())
        }
    }
    
    with open(os.path.join(base_path, "metadata.yaml"), "w") as f:
        yaml.dump(metadata, f)
        
    # 2. Create skill.md (Instructions)
    # We create a simple prompt-based skill wrapper
    content = f"""---
description: {skill.description}
---
# {skill.name}

{skill.instructions}

"""
    with open(os.path.join(base_path, "skill.md"), "w") as f:
        f.write(content)

    # 3. Reload Skill Manager (Hot Reload)
    # NOTE: In a real system we'd want a safer way, but this works for PoC
    try:
        system.skill_manager.load_skills()
        # Also update the session's loaded skills if needed, 
        # but simpler to just say "Restart might be needed for full effect"
        # actually skill_manager.skills is a global dict ref, so it might just work!
    except Exception as e:
        logger.error(f"Failed to hot-load skills: {e}")

    return {"status": "created", "path": base_path}

# --- Knowledge Base Management ---
from fastapi import UploadFile, File

@app.get("/knowledge", response_class=HTMLResponse)
async def knowledge_ui(request: Request):
    count = 0
    if system.agent_manager.vector_db:
        count = system.agent_manager.vector_db.count()
    return templates.TemplateResponse("knowledge.html", {"request": request, "doc_count": count})

@app.post("/api/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    if not system.agent_manager.vector_db:
        return {"error": "Vector DB not initialized"}
    
    try:
        content = await file.read()
        text = ""
        
        # Simple extraction based on extension
        filename = file.filename.lower()
        if filename.endswith(".pdf"):
             # TODO: specific PDF extraction using pypdf or similar
             # For now, treat as binary/error or try raw strings if mostly text
             # Actually, let's just fail specificially for PDF if we don't have a library
             # But to be robust for "demo", let's try to decode as utf-8 (works for txt/md)
             return {"error": "PDF parsing not yet implemented. Please upload .txt or .md"}
        else:
             # Assume text
             try:
                 text = content.decode("utf-8")
             except UnicodeDecodeError:
                 return {"error": "File must be UTF-8 text"}

        if not text.strip():
            return {"error": "File is empty"}
            
        # Add to Vector DB
        metadata = {"source": "upload", "filename": file.filename}
        doc_id = system.agent_manager.vector_db.add_document(text, metadata)
        
        return {"status": "success", "doc_id": doc_id, "filename": file.filename}

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return {"error": str(e)}

# --- Settings Management ---
class SettingsUpdate(BaseModel):
    system_prompt: str
    api_key: str = ""

@app.get("/settings", response_class=HTMLResponse)
async def settings_ui(request: Request):
    # Get current prompt from a fresh session or default
    # Since AgentManager creates sessions on fly, we might need a "default_system_prompt" stored on manager
    # For now, let's assume AgentManager has a 'default_system_prompt' attribute we added in Phase 4 
    # OR we just check the first session.
    # Actually, AgentManager.execute_agent uses a hardcoded or internal prompt construction.
    # We should expose a 'base_system_prompt' on AgentManager.
    
    current = getattr(system.agent_manager, "base_system_prompt", "You are OSP, a helpful AI assistant.")
    return templates.TemplateResponse("settings.html", {"request": request, "current_prompt": current})

@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    # Update prompt
    system.agent_manager.base_system_prompt = settings.system_prompt
    
    # Update API Key if provided
    if settings.api_key.strip():
        os.environ["GEMINI_API_KEY"] = settings.api_key.strip()
        # Trigger reload of LLM provider if needed?
        # Ideally we should re-init the LLM provider, but simplest is just setting env var for next call
        
    return {"status": "updated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
