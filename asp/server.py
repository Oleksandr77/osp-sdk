"""
OSP Server — Zero-Config Skill Server
=======================================
Start an OSP server with a single function call.

Usage::

    from asp import skill, serve

    @skill("greet", description="Say hello")
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    serve()  # Starts on http://localhost:8080
"""

import json
import sys
import os
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any

logger = logging.getLogger("asp.server")


class ASPServer:
    """
    Open Skills Protocol (OSP) server.
    Routes JSON-RPC requests through the OSP 4-stage pipeline.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, dev_mode: bool = False):
        self.host = host
        self.port = port
        self.dev_mode = dev_mode or os.environ.get("ASP_MODE", "") == "dev"
        self._router = None
        self._skills = {}

    def _lazy_init_router(self):
        """Lazy-load the full routing engine."""
        if self._router is None:
            try:
                from osp_server.logic.routing import RouterService
                self._router = RouterService()
            except ImportError:
                self._router = None

    def _get_candidates(self):
        """Build candidate list from registered skills."""
        from asp.decorators import get_registered_skills
        skills = get_registered_skills()
        return [s.to_candidate() for s in skills.values()]

    def _handle_route(self, params: dict) -> dict:
        """Route a query through the ASP pipeline."""
        self._lazy_init_router()

        query = params.get("query", "")
        candidates = params.get("candidate_skills") or self._get_candidates()

        if self._router:
            result = self._router.route({
                "query": query,
                "candidate_skills": candidates,
                "context": params.get("context", {}),
                "routing_conditions": params.get("routing_conditions", {}),
            })
            return result
        else:
            # Lightweight fallback: simple keyword match
            from asp.decorators import get_registered_skills
            skills = get_registered_skills()
            query_lower = query.lower()
            best_skill = None
            best_score = 0

            for sid, s in skills.items():
                score = 0
                for kw in s.keywords:
                    if kw.lower() in query_lower:
                        score += 1
                if s.skill_id.lower() in query_lower:
                    score += 2
                if score > best_score:
                    best_score = score
                    best_skill = s

            if best_skill:
                return {
                    "skill_ref": best_skill.skill_id,
                    "safety_clearance": "allow",
                    "approximate": best_score < 2,
                    "decision_stability": "keyword_match",
                    "trace_events": [{"code": "LIGHTWEIGHT_ROUTE", "stage_attempted": 0}],
                }
            return {
                "skill_ref": None,
                "safety_clearance": "escalate",
                "approximate": False,
                "decision_stability": "no_candidates",
                "trace_events": [{"code": "ROUTING_POOL_EMPTY", "stage_attempted": 0}],
            }

    def _handle_execute(self, params: dict) -> dict:
        """Execute a skill by ID."""
        from asp.decorators import get_registered_skills
        skills = get_registered_skills()

        skill_id = params.get("skill_id", "")
        skill_args = params.get("arguments", {})

        if skill_id not in skills:
            return {"error": f"Skill '{skill_id}' not found", "available": list(skills.keys())}

        try:
            result = skills[skill_id](**skill_args)
            return {"result": result, "skill_id": skill_id, "status": "success"}
        except Exception as e:
            return {"error": str(e), "skill_id": skill_id, "status": "error"}

    def _handle_list_skills(self) -> dict:
        """List all registered skills."""
        from asp.decorators import get_registered_skills
        skills = get_registered_skills()
        return {
            "skills": [s.to_manifest() for s in skills.values()],
            "count": len(skills),
            "protocol": "OSP/1.0",
        }

    def _handle_health(self) -> dict:
        """Health check."""
        from asp.decorators import get_registered_skills
        return {
            "status": "healthy",
            "protocol": "OSP/1.0",
            "version": "0.1.0",
            "skills_loaded": len(get_registered_skills()),
            "dev_mode": self.dev_mode,
        }

    def _handle_jsonrpc(self, body: dict) -> dict:
        """Process a JSON-RPC 2.0 request."""
        method = body.get("method", "")
        params = body.get("params", {})
        req_id = body.get("id", 1)

        handlers = {
            "asp.route": lambda: self._handle_route(params),
            "asp.execute": lambda: self._handle_execute(params),
            "asp.list_skills": lambda: self._handle_list_skills(),
            "asp.health": lambda: self._handle_health(),
        }

        if method in handlers:
            result = handlers[method]()
            return {"jsonrpc": "2.0", "result": result, "id": req_id}
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": req_id,
            }

    def create_handler(self):
        """Create HTTP request handler class."""
        server = self

        class ASPHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                if server.dev_mode:
                    logger.info(format % args)

            def _send_json(self, data: dict, status: int = 200):
                body = json.dumps(data, indent=2).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def do_GET(self):
                if self.path == "/health" or self.path == "/":
                    self._send_json(server._handle_health())
                elif self.path == "/skills":
                    self._send_json(server._handle_list_skills())
                elif self.path == "/_dashboard":
                    self._serve_dashboard()
                else:
                    self._send_json({"error": "Not found"}, 404)

            def do_POST(self):
                if self.path == "/asp-rpc":
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length)
                    try:
                        data = json.loads(body)
                        result = server._handle_jsonrpc(data)
                        self._send_json(result)
                    except json.JSONDecodeError:
                        self._send_json({"error": "Invalid JSON"}, 400)
                else:
                    self._send_json({"error": "Not found"}, 404)

            def _serve_dashboard(self):
                """Serve the built-in interactive dashboard."""
                from asp.decorators import get_registered_skills
                skills = get_registered_skills()

                skill_rows = ""
                for s in skills.values():
                    kw = ", ".join(s.keywords[:3]) if s.keywords else "—"
                    skill_rows += f"""
                    <tr>
                        <td><code>{s.skill_id}</code></td>
                        <td>{s.description}</td>
                        <td>{kw}</td>
                        <td><span class="badge badge-{s.risk_level.lower()}">{s.risk_level}</span></td>
                        <td>v{s.version}</td>
                    </tr>"""

                html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSP Dashboard — Open Skills Protocol</title>
<style>
:root {{
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface2: #1a1a2e;
    --border: #2a2a3e;
    --text: #e0e0f0;
    --text-dim: #8888aa;
    --accent: #6c5ce7;
    --accent2: #a29bfe;
    --success: #00b894;
    --warning: #fdcb6e;
    --danger: #ff6b6b;
    --gradient: linear-gradient(135deg, #6c5ce7, #a29bfe);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}}
.header {{
    padding: 24px 32px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.header h1 {{
    font-size: 1.4rem;
    background: var(--gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
}}
.header .status {{
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--success);
    font-size: 0.85rem;
}}
.header .dot {{
    width: 8px; height: 8px;
    background: var(--success);
    border-radius: 50%;
    animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
}}
.container {{ max-width: 1200px; margin: 0 auto; padding: 24px 32px; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
.card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
}}
.card h2 {{
    font-size: 0.85rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
}}
.stat {{ font-size: 2rem; font-weight: 700; color: var(--accent2); }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ color: var(--text-dim); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
td code {{ color: var(--accent2); background: var(--surface2); padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; }}
.badge {{
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}}
.badge-low {{ background: rgba(0,184,148,0.15); color: var(--success); }}
.badge-medium {{ background: rgba(253,203,110,0.15); color: var(--warning); }}
.badge-high {{ background: rgba(255,107,107,0.15); color: var(--danger); }}
.badge-critical {{ background: rgba(255,50,50,0.2); color: #ff4444; }}
.test-box {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-top: 24px;
}}
.test-box h2 {{ font-size: 0.85rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }}
.test-input {{ display: flex; gap: 12px; }}
.test-input input {{
    flex: 1;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    color: var(--text);
    font-size: 0.95rem;
    outline: none;
}}
.test-input input:focus {{ border-color: var(--accent); }}
.test-input button {{
    background: var(--gradient);
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    color: white;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
}}
.test-input button:hover {{ opacity: 0.85; }}
#result {{
    margin-top: 12px;
    padding: 14px;
    background: var(--surface2);
    border-radius: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    white-space: pre-wrap;
    color: var(--text-dim);
    max-height: 300px;
    overflow-y: auto;
    display: none;
}}
</style>
</head>
<body>
<div class="header">
    <h1>⚡ Open Skills Protocol</h1>
    <div class="status"><div class="dot"></div> Running {'(dev mode)' if server.dev_mode else ''}</div>
</div>
<div class="container">
    <div class="grid">
        <div class="card"><h2>Skills Loaded</h2><div class="stat">{len(skills)}</div></div>
        <div class="card"><h2>Protocol Version</h2><div class="stat">OSP/1.0</div></div>
    </div>
    <div class="card">
        <h2>Registered Skills</h2>
        <table>
            <thead><tr><th>ID</th><th>Description</th><th>Keywords</th><th>Risk</th><th>Version</th></tr></thead>
            <tbody>{skill_rows or '<tr><td colspan="5" style="color:var(--text-dim);text-align:center;">No skills registered. Use @skill decorator to add skills.</td></tr>'}</tbody>
        </table>
    </div>
    <div class="test-box">
        <h2>🧪 Test Console</h2>
        <div class="test-input">
            <input type="text" id="query" placeholder="Type a query to route..." onkeypress="if(event.key==='Enter')testRoute()">
            <button onclick="testRoute()">Route →</button>
        </div>
        <pre id="result"></pre>
    </div>
</div>
<script>
async function testRoute() {{
    const q = document.getElementById('query').value;
    const el = document.getElementById('result');
    el.style.display = 'block';
    el.textContent = 'Routing...';
    try {{
        const res = await fetch('/asp-rpc', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{jsonrpc: '2.0', method: 'asp.route', params: {{query: q}}, id: 1}})
        }});
        const data = await res.json();
        el.textContent = JSON.stringify(data.result || data.error, null, 2);
    }} catch(e) {{
        el.textContent = 'Error: ' + e.message;
    }}
}}
</script>
</body>
</html>"""
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())

        return ASPHandler

    def run(self):
        """Start the server."""
        from asp.decorators import get_registered_skills
        skills = get_registered_skills()

        handler = self.create_handler()
        httpd = HTTPServer((self.host, self.port), handler)

        print(f"""
\033[95m⚡ Open Skills Protocol (OSP) Server\033[0m
\033[90m{'─' * 45}\033[0m
  🌐 Server:    \033[96mhttp://localhost:{self.port}\033[0m
  📡 JSON-RPC:  \033[96mhttp://localhost:{self.port}/asp-rpc\033[0m
  📊 Dashboard: \033[96mhttp://localhost:{self.port}/_dashboard\033[0m
  💚 Health:    \033[96mhttp://localhost:{self.port}/health\033[0m
\033[90m{'─' * 45}\033[0m
  Skills loaded: \033[93m{len(skills)}\033[0m
  Mode: \033[93m{'🔧 Development' if self.dev_mode else '🔒 Production'}\033[0m
\033[90m{'─' * 45}\033[0m
  Press Ctrl+C to stop
""")
        for s in skills.values():
            print(f"  ✅ \033[96m{s.skill_id}\033[0m — {s.description}")
        print()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\033[93m⏹ Server stopped.\033[0m")
            httpd.server_close()


def serve(host: str = "0.0.0.0", port: int = 8080, dev_mode: bool = False):
    """
    Start an ASP server with all registered skills.

    This is the simplest way to run your skills::

        from asp import skill, serve

        @skill("greet", description="Say hello")
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        serve()  # → http://localhost:8080
    """
    server = ASPServer(host=host, port=port, dev_mode=dev_mode)
    server.run()
