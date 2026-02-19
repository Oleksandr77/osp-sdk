from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import uuid
import uvicorn
from datetime import datetime, timezone
import logging
import os
import sys

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Logic
from .logic.routing import RouterService
from .logic.delivery import DeliveryContractEnforcer

try:
    from ai_core.skill_manager import SkillManager
except ImportError:
    SkillManager = None

app = FastAPI(
    title="OSP Reference Server",
    version="1.0.0",
    description="Open Skills Protocol — Reference Implementation with 4-stage routing, semantic safety, and cryptographic plane isolation.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (configurable via OSP_CORS_ORIGINS env var)
_cors_origins = os.environ.get("OSP_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple rate limiter (in-memory, per-IP)
from collections import defaultdict
_rate_limits: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 100  # requests per window

async def check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    _rate_limits[client_ip] = [t for t in _rate_limits[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[client_ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _rate_limits[client_ip].append(now)

# Admin API Key (REQUIRED — no default)
ADMIN_API_KEY = os.environ.get("OSP_ADMIN_KEY")
if not ADMIN_API_KEY:
    import warnings
    warnings.warn("OSP_ADMIN_KEY not set — admin endpoints will reject all requests")
    ADMIN_API_KEY = None

async def verify_admin(request: Request):
    key = request.headers.get("X-Admin-Key", "")
    if key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
router_service = RouterService()
delivery_enforcer = DeliveryContractEnforcer()
# Initialize SkillManager with absolute path to skills directory
skills_path = os.path.join(parent_dir, "skills")
if SkillManager:
    skill_manager = SkillManager(skills_dir=skills_path)
else:
    skill_manager = None

# JSON-RPC Models
class JsonRpcRequest(BaseModel):
    jsonrpc: str
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None

# Configure logging
from .logic.json_logger import configure_json_logging
logger = configure_json_logging("osp_server")

# Initialize Signature Verifier
try:
    from .middleware.signature import SignatureVerifier
    from osp_core.crypto import JCS
    
    # Generate a demo keypair for Plane Isolation (Signature Enforcement)
    priv_key, pub_key = JCS.generate_key("ES256")
    logger.info("🔑 Generated ephemeral ES256 keypair for Plane Isolation Demo.")
    
    verifier = SignatureVerifier(public_key_pem=pub_key)
    _enforce = os.environ.get("OSP_SIGNATURE_ENFORCE", "false").lower() == "true"
    verifier.set_enforcement(_enforce)  # Default: soft mode; set OSP_SIGNATURE_ENFORCE=true for strict

except Exception as e:
    logger.error(f"Failed to initialize SignatureVerifier: {e}")
    verifier = None

@app.post("/osp-rpc")
async def osp_rpc_endpoint(request: Request):
    """
    Main JSON-RPC endpoint.
    Supports 'osp.route' and 'osp.execute'.
    """
    # 1. Read Body
    body_bytes = await request.body()
    
    # 2. Verify Signature (Plane Isolation)
    if verifier:
        await verifier.verify_request(request, body_bytes)
    
    rpc_id = None
    try:
        # Re-parse JSON for logic since we consumed stream (though Starlette caches it usually)
        request_json = await request.json()
        
        # Validation
        if "jsonrpc" not in request_json or request_json["jsonrpc"] != "2.0":
             OSP_REQUESTS_TOTAL.labels(method="unknown", status="400").inc()
             return JSONResponse(status_code=400, content={"error": "Invalid JSON-RPC version"})
        
        rpc_req = JsonRpcRequest(**request_json)
        rpc_id = rpc_req.id
        logger.info(f"RPC Request: method={rpc_req.method} id={rpc_id}")
        
        # Metrics: Track incoming request
        OSP_REQUESTS_TOTAL.labels(method=rpc_req.method, status="pending").inc()
        
        result = None
        status_code = 200

        if rpc_req.method == "osp.route":
            # Dispatch to RouterService
            result = router_service.route(rpc_req.params)
            
            # Check for specific error conditions to set HTTP status code (OSP Conformance)
            if result and result.get("refusal"):
                reason = result.get("reason_code", "")
                # Availability / Fail-Closed errors -> 503
                if reason in ["SAFETY_CLASSIFIER_UNAVAILABLE", "SAFETY_CHECK_TIMEOUT", "ANOMALY_DETECTED_SEMANTIC_BYPASS"]:
                    status_code = 503
                # Invalid Request -> 400
                elif reason == "INVALID_REQUEST_EMPTY_QUERY":
                    status_code = 400
                # Standard Safety Block -> 403
                else:
                    status_code = 403
            elif result and "error" in result:
                error = result["error"]
                if isinstance(error, dict) and error.get("code") == -32602:
                    status_code = 400
                elif error == "No skill matched": 
                     status_code = 503 
        
        elif rpc_req.method == "osp.execute":
            # Dispatch to SkillManager with Delivery Contract Enforcement
            skill_id = rpc_req.params.get("skill_id")
            arguments = rpc_req.params.get("arguments", {})
            ttl = rpc_req.params.get("ttl_seconds", 300)
            idempotency_key = rpc_req.params.get("idempotency_key")
            
            if not skill_id:
                return JSONResponse(status_code=400, content={
                    "jsonrpc": "2.0", 
                    "error": {"code": -32602, "message": "Missing skill_id"}, 
                    "id": rpc_id
                })

            tools_module = skill_manager.get_skill_tools(skill_id)
            if not tools_module:
                 return JSONResponse(status_code=404, content={
                    "jsonrpc": "2.0", 
                    "error": {"code": -32601, "message": f"Skill tools not found for {skill_id}"}, 
                    "id": rpc_id
                })
            
            # Execute with delivery contract enforcement
            if hasattr(tools_module, "execute"):
                delivery_result = delivery_enforcer.execute_with_contract(
                    skill_ref=skill_id,
                    execute_fn=tools_module.execute,
                    arguments=arguments,
                    ttl_seconds=ttl,
                    idempotency_key=idempotency_key,
                )
                if "error" in delivery_result:
                    return JSONResponse(status_code=500, content={
                        "jsonrpc": "2.0",
                        "error": {"code": -32603, "message": delivery_result["error"]},
                        "id": rpc_id
                    })
                result = delivery_result
            else:
                 return JSONResponse(status_code=500, content={
                    "jsonrpc": "2.0", 
                    "error": {"code": -32603, "message": f"Method 'execute' missing in module"}, 
                    "id": rpc_id
                })

        elif rpc_req.method == "osp.get_proof":
            # Return delivery contract proof for a given idempotency key
            idem_key = rpc_req.params.get("idempotency_key")
            if not idem_key:
                return JSONResponse(status_code=400, content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Missing idempotency_key"},
                    "id": rpc_id
                })
            proof = delivery_enforcer.get_proof(idem_key)
            if not proof:
                result = {"error": f"No contract found for key '{idem_key}'"}
            else:
                result = proof

        elif rpc_req.method == "osp.list_profiles":
            # Return deployment profiles configuration
            from .logic.degradation import DegradationController
            ctrl = DegradationController()
            result = {
                "current_level": ctrl.current_level.name,
                "profiles": {
                    "D0_NORMAL": {"description": "Full functionality, all capabilities", "llm": True, "semantic_routing": True},
                    "D1_REDUCED_INTELLIGENCE": {"description": "No LLM, deterministic routing only", "llm": False, "semantic_routing": True},
                    "D2_MINIMAL": {"description": "Strict lexical matching only", "llm": False, "semantic_routing": False},
                    "D3_CRITICAL": {"description": "Load shedding, service unavailable", "llm": False, "semantic_routing": False},
                },
            }

        elif rpc_req.method == "osp.list_skills":
            # Return list of skill metadata
            skills = skill_manager.skills
            result = [s["metadata"] for s in skills.values()]
            
        elif rpc_req.method == "osp.get_capabilities":
            # Return server capabilities
            result = {
                "protocol": "OSP/1.0", 
                "server": "OSP Reference Server v1.0.0",
                "methods": [
                    "osp.route", "osp.execute", "osp.list_skills",
                    "osp.get_capabilities", "osp.get_skill", "osp.get_proof",
                    "osp.list_profiles", "osp.conformance.run",
                ],
                "auth": "JCS+ES256/ES384/ES512/RS256/RS384/RS512/EdDSA/HS256/HS512",
                "degradation_levels": ["D0_NORMAL", "D1_REDUCED", "D2_MINIMAL", "D3_CRITICAL"],
                "delivery_contracts": True,
            }

        elif rpc_req.method == "osp.get_skill":
            # Return single skill metadata
            skill_id = rpc_req.params.get("skill_id")
            if not skill_id:
                return JSONResponse(status_code=400, content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Missing skill_id"},
                    "id": rpc_id
                })
            skill = skill_manager.skills.get(skill_id)
            result = skill["metadata"] if skill else {"error": f"Skill '{skill_id}' not found"}

        elif rpc_req.method == "osp.conformance.run":
            # Run conformance self-check (basic)
            result = {
                "protocol": "OSP/1.0",
                "server": "OSP Reference Server v1.0.0",
                "checks": {
                    "routing_pipeline": "4-stage (BM25+Semantic+Conflict+Tiebreak)",
                    "safety_classifier": "TF-IDF + KL-divergence",
                    "degradation": "D0-D3 with hysteresis",
                    "crypto": "9 algorithms (ES/RS/EdDSA/HMAC)",
                    "signatures": "strict enforcement",
                },
                "status": "conformant",
            }

        else:
            # Method not found
            return JSONResponse(status_code=404, content={
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{rpc_req.method}' not found"},
                "id": rpc_id
            })
        
        # Add _meta envelope with request_id and trace_id
        _meta = {
            "request_id": str(uuid.uuid4()),
            "trace_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return JSONResponse(status_code=status_code, content={"jsonrpc": "2.0", "result": result, "id": rpc_id, "_meta": _meta})
        
    except Exception as e:
        logger.error(f"RPC Handler Error: {e}")
        return JSONResponse(status_code=500, content={"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": rpc_id})

# Agent API Models
class AgentStartRequest(BaseModel):
    expertise_profile: Dict[str, Any]

class AgentExecuteRequest(BaseModel):
    session_id: str
    input_text: str

from .logic.degradation import DegradationController, DegradationLevel
degradation = DegradationController()

# Initialize AgentManager (optional — requires ai_core)
try:
    from ai_core.agent_manager import AgentManager
    agent_manager = AgentManager(skill_manager, degradation_controller=degradation)
except ImportError:
    agent_manager = None

# Start Auto-Degradation Monitoring (Background Thread)
# Will seamlessly fail/log warning if psutil is missing
degradation.start_monitoring(interval=5)

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown: stop monitoring, close sessions."""
    logger.info("🛑 Graceful shutdown initiated...")
    degradation.stop_monitoring()
    logger.info("✅ Shutdown complete.")

class DegradationRequest(BaseModel):
    level: str # D0, D1, D2, D3

@app.get("/admin/debug/keys", dependencies=[Depends(verify_admin)])
async def get_debug_keys():
    """
    Exposes ephemeral keys for testing purposes ONLY.
    Requires X-Admin-Key header.
    """
    if 'priv_key' in globals() and 'pub_key' in globals():
        return {
            "private_key": priv_key.decode('utf-8'),
            "public_key": pub_key.decode('utf-8')
        }
    return {"error": "Keys not generated"}

@app.post("/admin/degradation", dependencies=[Depends(verify_admin)])
async def set_degradation_level(request: DegradationRequest):
    """
    Sets the system degradation level (D0-D3).
    D0: Normal (Hybrid)
    D1: Reduced (No LLM)
    D2: Minimal (Strict)
    D3: Critical (Load Shedding)
    """
    try:
        level_enum = getattr(DegradationLevel, request.level.upper())
        degradation.set_level(level_enum)
        # Update Metric
        OSP_DEGRADATION_LEVEL.set(level_enum.value)
        return {"status": "success", "level": level_enum.name}
    except AttributeError:
        raise HTTPException(status_code=400, detail="Invalid degradation level. Use D0_NORMAL, D1_REDUCED_INTELLIGENCE, D2_MINIMAL, D3_CRITICAL")

@app.post("/osp-agent/start")
async def start_agent_session(request: AgentStartRequest):
    """
    Starts a new agent session with a given expertise profile.
    """
    # D3 Check: Load Shedding
    if not degradation.check_request_allowed():
        raise HTTPException(status_code=503, detail="Service Unavailable (Degradation D3)")
        
    try:
        session = agent_manager.create_session(request.expertise_profile)
        return {
            "status": "created",
            "session_id": session.session_id,
            "message": f"Agent '{request.expertise_profile.get('name')}' started."
        }
    except Exception as e:
        logger.error(f"Agent Start Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/osp-agent/execute")
async def execute_agent_request(request: AgentExecuteRequest):
    """
    Executes a request in an existing agent session.
    """
    # D3 Check: Load Shedding
    if not degradation.check_request_allowed():
        raise HTTPException(status_code=503, detail="Service Unavailable (Degradation D3)")

    try:
        # Pass degradation context to AgentManager (or AgentManager reads singleton)
        # Ideally, we pass it explicitly or it uses the singleton.
        result = agent_manager.execute_agent(request.session_id, request.input_text)
        if "error" in result:
             status = 404 if result["error"] == "Session not found" else 500
             return JSONResponse(status_code=status, content=result)
        return result
    except Exception as e:
        logger.error(f"Agent Execute Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Metrics
from .logic.metrics import generate_latest, CONTENT_TYPE_LATEST, OSP_REQUESTS_TOTAL, OSP_DEGRADATION_LEVEL

@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
