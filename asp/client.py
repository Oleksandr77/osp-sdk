"""
ASP Client — Connect to any ASP server
========================================
Usage::

    from asp import ASPClient

    client = ASPClient("http://localhost:8080")
    result = client.route("What's the weather?")
    result = client.execute("weather", city="Kyiv")
    skills = client.list_skills()
"""

import json
import urllib.request
from typing import Any, Dict, Optional


class ASPClient:
    """Client for connecting to an ASP server."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self._req_id = 0

    def _rpc(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request."""
        self._req_id += 1
        body = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._req_id,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/asp-rpc",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        if "error" in data:
            raise ASPError(data["error"].get("message", "Unknown error"))

        return data.get("result", {})

    def route(self, query: str, **kwargs) -> Dict[str, Any]:
        """Route a query through the ASP pipeline."""
        params = {"query": query, **kwargs}
        return self._rpc("asp.route", params)

    def execute(self, skill_id: str, **arguments) -> Any:
        """Execute a skill by ID with arguments."""
        return self._rpc("asp.execute", {"skill_id": skill_id, "arguments": arguments})

    def list_skills(self) -> Dict[str, Any]:
        """List all available skills."""
        return self._rpc("asp.list_skills")

    def health(self) -> Dict[str, Any]:
        """Check server health."""
        req = urllib.request.Request(f"{self.base_url}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())

    def __repr__(self) -> str:
        return f"<ASPClient url='{self.base_url}'>"


class ASPError(Exception):
    """Error from ASP server."""
    pass
