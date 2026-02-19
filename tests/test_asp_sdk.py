"""
Comprehensive test suite for the ASP SDK.
Covers: decorators, server, client, CLI, integration, package.

All tests use a single shared server instance to avoid port conflicts.
"""
import unittest
import json
import threading
import time
import urllib.request
import sys
import os
import tempfile

# Add project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# ── Shared Server Lifecycle ────────────────────────────────────
# We start ONE server before all tests and shut it down after all.

_SERVER = None
_HTTPD = None
_THREAD = None
SERVER_PORT = 19876


def _start_shared_server():
    """Start a single test server for the whole suite."""
    global _SERVER, _HTTPD, _THREAD

    from asp.decorators import _SKILL_REGISTRY, skill

    # Clear any previous test registrations
    _SKILL_REGISTRY.clear()

    @skill("srv.greet", description="Say hello", keywords=["hello", "greet"])
    def greet(name: str = "World") -> str:
        return f"Hello, {name}!"

    @skill("srv.add", description="Add numbers", keywords=["add", "sum", "math"])
    def add(a: int, b: int) -> int:
        return a + b

    @skill("srv.fail", description="Always fails", keywords=["error"])
    def fail_skill() -> str:
        raise ValueError("Intentional error")

    from asp.server import ASPServer
    from http.server import HTTPServer

    _SERVER = ASPServer(host="127.0.0.1", port=SERVER_PORT, dev_mode=True)
    handler = _SERVER.create_handler()
    _HTTPD = HTTPServer(("127.0.0.1", SERVER_PORT), handler)
    _THREAD = threading.Thread(target=_HTTPD.serve_forever, daemon=True)
    _THREAD.start()
    time.sleep(0.5)


def _stop_shared_server():
    global _HTTPD
    if _HTTPD:
        _HTTPD.shutdown()


def _rpc(method, params=None, req_id=1):
    """Helper: send a JSON-RPC request to the shared server."""
    body = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": req_id,
    }).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{SERVER_PORT}/asp-rpc",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req, timeout=10)
    return json.loads(r.read())


# ═══════════════════════════════════════════════════════════════
# 1. DECORATOR TESTS (no server needed)
# ═══════════════════════════════════════════════════════════════

class Test01_SkillDecorator(unittest.TestCase):
    """Test the @skill decorator: registration, parameter extraction, manifest."""

    def setUp(self):
        from asp.decorators import _SKILL_REGISTRY
        _SKILL_REGISTRY.clear()

    def test_basic_registration(self):
        """Decorating a function registers it in the global registry."""
        from asp.decorators import skill, get_registered_skills

        @skill("test.basic", description="A basic skill")
        def my_func(x: int) -> str:
            return str(x)

        skills = get_registered_skills()
        self.assertIn("test.basic", skills)
        self.assertEqual(skills["test.basic"].skill_id, "test.basic")
        self.assertEqual(skills["test.basic"].description, "A basic skill")

    def test_parameter_extraction_types(self):
        """Decorator auto-detects parameter types from annotations."""
        from asp.decorators import skill, get_registered_skills

        @skill("test.types")
        def typed_func(name: str, age: int, score: float, active: bool) -> str:
            return "ok"

        params = get_registered_skills()["test.types"].parameters
        self.assertEqual(params["name"]["type"], "string")
        self.assertEqual(params["age"]["type"], "integer")
        self.assertEqual(params["score"]["type"], "number")
        self.assertEqual(params["active"]["type"], "boolean")

    def test_required_vs_optional(self):
        """Parameters with defaults are optional; without are required."""
        from asp.decorators import skill, get_registered_skills

        @skill("test.req")
        def req_func(required_param: str, optional_param: str = "default") -> str:
            return "ok"

        params = get_registered_skills()["test.req"].parameters
        self.assertTrue(params["required_param"]["required"])
        self.assertFalse(params["optional_param"]["required"])

    def test_manifest_generation(self):
        """to_manifest() produces a valid ASP/1.0 manifest."""
        from asp.decorators import skill, get_registered_skills

        @skill("test.manifest", description="Manifest test", keywords=["a", "b"], risk_level="HIGH")
        def manifest_fn(x: int) -> str:
            return str(x)

        m = get_registered_skills()["test.manifest"].to_manifest()
        self.assertEqual(m["protocol"], "ASP/1.0")
        self.assertEqual(m["skill_id"], "test.manifest")
        self.assertEqual(m["description"], "Manifest test")
        self.assertEqual(m["activation_keywords"], ["a", "b"])
        self.assertEqual(m["risk_level"], "HIGH")
        self.assertIn("parameters", m)
        self.assertIn("x", m["parameters"])

    def test_candidate_dict(self):
        """to_candidate() produces a routing-compatible dict."""
        from asp.decorators import skill, get_registered_skills

        @skill("test_cand", description="Candidate", keywords=["kw1"])
        def cand_fn(y: float) -> str:
            return str(y)

        c = get_registered_skills()["test_cand"].to_candidate()
        self.assertEqual(c["skill_id"], "test_cand")
        self.assertEqual(c["description"], "Candidate")
        self.assertEqual(c["activation_keywords"], ["kw1"])
        # Name is title-cased from skill_id
        self.assertEqual(c["name"], "Test Cand")

    def test_execution_through_wrapper(self):
        """Calling the wrapper directly executes the underlying function."""
        from asp.decorators import skill

        @skill("test.exec")
        def add(a: int, b: int = 10) -> int:
            return a + b

        self.assertEqual(add(5), 15)
        self.assertEqual(add(5, b=20), 25)

    def test_multiple_skills_no_collision(self):
        """Multiple skills can be registered without collision."""
        from asp.decorators import skill, get_registered_skills

        @skill("multi.a")
        def fn_a() -> str:
            return "a"

        @skill("multi.b")
        def fn_b() -> str:
            return "b"

        @skill("multi.c")
        def fn_c() -> str:
            return "c"

        skills = get_registered_skills()
        self.assertEqual(len(skills), 3)

    def test_no_annotation_defaults_to_string(self):
        """Parameters without type annotations default to 'string'."""
        from asp.decorators import skill, get_registered_skills

        @skill("test.notype")
        def notype_fn(x) -> str:
            return str(x)

        params = get_registered_skills()["test.notype"].parameters
        self.assertEqual(params["x"]["type"], "string")

    def test_version_and_security(self):
        """Version and security fields are stored correctly."""
        from asp.decorators import skill, get_registered_skills

        @skill("test.ver", version="2.5.0", security="ES256")
        def ver_fn() -> str:
            return "ok"

        s = get_registered_skills()["test.ver"]
        self.assertEqual(s.version, "2.5.0")
        m = s.to_manifest()
        self.assertEqual(m["version"], "2.5.0")


# ═══════════════════════════════════════════════════════════════
# 2. SERVER TESTS (uses shared server)
# ═══════════════════════════════════════════════════════════════

class Test02_ASPServer(unittest.TestCase):
    """Test the ASP server: endpoints, JSON-RPC, dashboard."""

    @classmethod
    def setUpClass(cls):
        _start_shared_server()

    # ── Health ──────────────────────────────────
    def test_health_endpoint(self):
        """GET /health returns correct status."""
        r = urllib.request.urlopen(f"http://127.0.0.1:{SERVER_PORT}/health", timeout=5)
        data = json.loads(r.read())
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["protocol"], "OSP/1.0")
        self.assertEqual(data["skills_loaded"], 3)
        self.assertTrue(data["dev_mode"])

    # ── Route ──────────────────────────────────
    def test_route_greet(self):
        """Routing 'say hello' resolves to srv.greet."""
        resp = _rpc("asp.route", {"query": "say hello"})
        self.assertEqual(resp["result"]["skill_ref"], "srv.greet")
        self.assertIn("trace_events", resp["result"])

    def test_route_math(self):
        """Routing 'add numbers' resolves to srv.add."""
        resp = _rpc("asp.route", {"query": "add some numbers together"})
        self.assertEqual(resp["result"]["skill_ref"], "srv.add")

    def test_route_returns_trace(self):
        """Routing always returns trace_events for observability."""
        resp = _rpc("asp.route", {"query": "hello"})
        self.assertIsInstance(resp["result"]["trace_events"], list)
        self.assertGreater(len(resp["result"]["trace_events"]), 0)

    # ── Execute ────────────────────────────────
    def test_execute_greet(self):
        """Executing srv.greet returns correct result."""
        resp = _rpc("asp.execute", {
            "skill_id": "srv.greet",
            "arguments": {"name": "Oleksandr"},
        })
        self.assertEqual(resp["result"]["result"], "Hello, Oleksandr!")
        self.assertEqual(resp["result"]["status"], "success")

    def test_execute_add(self):
        """Executing srv.add with integers returns sum."""
        resp = _rpc("asp.execute", {
            "skill_id": "srv.add",
            "arguments": {"a": 3, "b": 7},
        })
        self.assertEqual(resp["result"]["result"], 10)
        self.assertEqual(resp["result"]["status"], "success")

    def test_execute_default_param(self):
        """Executing with default params fills in the default value."""
        resp = _rpc("asp.execute", {
            "skill_id": "srv.greet",
            "arguments": {},
        })
        self.assertEqual(resp["result"]["result"], "Hello, World!")

    def test_execute_unknown_skill(self):
        """Executing non-existent skill returns error in result."""
        resp = _rpc("asp.execute", {
            "skill_id": "nonexistent",
            "arguments": {},
        })
        # Error is inside result, not a top-level error
        self.assertIn("error", resp["result"])
        self.assertIn("nonexistent", resp["result"]["error"])

    def test_execute_skill_error_handling(self):
        """Executing a skill that raises returns error status."""
        resp = _rpc("asp.execute", {
            "skill_id": "srv.fail",
            "arguments": {},
        })
        self.assertEqual(resp["result"]["status"], "error")
        self.assertIn("Intentional error", resp["result"]["error"])

    # ── List Skills ────────────────────────────
    def test_list_skills(self):
        """asp.list_skills returns all registered skills."""
        resp = _rpc("asp.list_skills")
        self.assertEqual(resp["result"]["count"], 3)
        skill_ids = [s["skill_id"] for s in resp["result"]["skills"]]
        self.assertIn("srv.greet", skill_ids)
        self.assertIn("srv.add", skill_ids)
        self.assertIn("srv.fail", skill_ids)

    def test_list_skills_have_params(self):
        """Listed skills include their parameters."""
        resp = _rpc("asp.list_skills")
        greet_skill = [s for s in resp["result"]["skills"] if s["skill_id"] == "srv.greet"][0]
        self.assertIn("parameters", greet_skill)
        self.assertIn("name", greet_skill["parameters"])

    # ── Dashboard ──────────────────────────────
    def test_dashboard_endpoint(self):
        """GET /_dashboard returns HTML with OSP branding."""
        r = urllib.request.urlopen(f"http://127.0.0.1:{SERVER_PORT}/_dashboard", timeout=5)
        html = r.read().decode()
        self.assertIn("Open Skills Protocol", html)
        self.assertIn("srv.greet", html)
        self.assertGreater(len(html), 1000)

    # ── Unknown Method ─────────────────────────
    def test_unknown_method(self):
        """Unknown JSON-RPC method returns error."""
        resp = _rpc("asp.unknown_method")
        self.assertIn("error", resp)

    # ── Skills Endpoint ────────────────────────
    def test_skills_get_endpoint(self):
        """GET /skills returns JSON skill list."""
        r = urllib.request.urlopen(f"http://127.0.0.1:{SERVER_PORT}/skills", timeout=5)
        data = json.loads(r.read())
        self.assertEqual(data["count"], 3)


# ═══════════════════════════════════════════════════════════════
# 3. CLIENT TESTS (uses shared server)
# ═══════════════════════════════════════════════════════════════

class Test03_ASPClient(unittest.TestCase):
    """Test the ASP client against the running test server."""

    def test_client_health(self):
        """Client health check returns status."""
        from asp.client import ASPClient
        client = ASPClient(f"http://127.0.0.1:{SERVER_PORT}")
        result = client.health()
        self.assertEqual(result["status"], "healthy")

    def test_client_route(self):
        """Client routing finds correct skill."""
        from asp.client import ASPClient
        client = ASPClient(f"http://127.0.0.1:{SERVER_PORT}")
        result = client.route("say hello")
        self.assertEqual(result["skill_ref"], "srv.greet")

    def test_client_execute(self):
        """Client execution returns result."""
        from asp.client import ASPClient
        client = ASPClient(f"http://127.0.0.1:{SERVER_PORT}")
        result = client.execute("srv.greet", name="Client")
        self.assertEqual(result["result"], "Hello, Client!")

    def test_client_list_skills(self):
        """Client list_skills returns skills."""
        from asp.client import ASPClient
        client = ASPClient(f"http://127.0.0.1:{SERVER_PORT}")
        result = client.list_skills()
        self.assertEqual(result["count"], 3)


# ═══════════════════════════════════════════════════════════════
# 4. CLI TESTS (no server needed)
# ═══════════════════════════════════════════════════════════════

class Test04_ASPCLI(unittest.TestCase):
    """Test the ASP CLI commands."""

    def _get_env(self):
        """Get environment with PYTHONPATH set."""
        env = os.environ.copy()
        env["PYTHONPATH"] = PROJECT_ROOT
        return env

    def test_cli_version(self):
        """asp --version prints version."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "asp.cli", "--version"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
            env=self._get_env(),
        )
        self.assertIn("0.1.0", result.stdout + result.stderr)

    def test_cli_skills_command(self):
        """asp skills <file> lists skills from a file."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "asp.cli", "skills", "examples/hello.py"],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT,
            env=self._get_env(),
        )
        output = result.stdout + result.stderr
        self.assertIn("greet", output)

    def test_cli_init_scaffold(self):
        """asp init creates a project directory with example files."""
        import subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            project_name = "test_asp_project"
            result = subprocess.run(
                [sys.executable, "-m", "asp.cli", "init", project_name],
                capture_output=True, text=True,
                cwd=tmpdir,
                env=self._get_env(),
            )
            project_dir = os.path.join(tmpdir, project_name)
            self.assertTrue(
                os.path.isdir(project_dir),
                f"Project dir not created.\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )
            self.assertTrue(os.path.isfile(os.path.join(project_dir, "main.py")))
            self.assertTrue(os.path.isfile(os.path.join(project_dir, "README.md")))


# ═══════════════════════════════════════════════════════════════
# 5. INTEGRATION TESTS (uses shared server)
# ═══════════════════════════════════════════════════════════════

class Test05_Integration(unittest.TestCase):
    """End-to-end integration tests for the full ASP stack."""

    def test_route_then_execute(self):
        """Route a query, then execute the matched skill."""
        from asp.client import ASPClient
        client = ASPClient(f"http://127.0.0.1:{SERVER_PORT}")

        # Route
        route_result = client.route("add numbers")
        skill_id = route_result["skill_ref"]
        self.assertEqual(skill_id, "srv.add")

        # Execute the routed skill
        exec_result = client.execute(skill_id, a=10, b=32)
        self.assertEqual(exec_result["result"], 42)
        self.assertEqual(exec_result["status"], "success")

    def test_full_flow_with_trace(self):
        """Full flow: route → get trace → verify decision chain."""
        from asp.client import ASPClient
        client = ASPClient(f"http://127.0.0.1:{SERVER_PORT}")

        result = client.route("greet someone")
        trace = result.get("trace_events", [])
        trace_codes = [t["code"] for t in trace]
        self.assertIn("SAFETY_CHECK_PASS", trace_codes)
        self.assertIn("ROUTING_DECISION_FINAL", trace_codes)


# ═══════════════════════════════════════════════════════════════
# 6. PACKAGE TESTS (no server needed)
# ═══════════════════════════════════════════════════════════════

class Test06_Package(unittest.TestCase):
    """Test the asp package structure and exports."""

    def test_version_defined(self):
        """asp.__version__ is defined."""
        from asp import __version__
        self.assertIsInstance(__version__, str)
        self.assertRegex(__version__, r"\d+\.\d+\.\d+")

    def test_protocol_defined(self):
        """asp.__protocol__ is defined."""
        from asp import __protocol__
        self.assertEqual(__protocol__, "Open Skills Protocol")

    def test_public_api_exports(self):
        """All public symbols are importable."""
        from asp import skill, serve, ASPServer, ASPClient
        self.assertTrue(callable(skill))
        self.assertTrue(callable(serve))

    def test_all_modules_importable(self):
        """All ASP sub-modules can be imported."""
        import asp.decorators
        import asp.server
        import asp.client
        import asp.cli
        self.assertTrue(hasattr(asp.decorators, "skill"))
        self.assertTrue(hasattr(asp.server, "ASPServer"))
        self.assertTrue(hasattr(asp.client, "ASPClient"))
        self.assertTrue(hasattr(asp.cli, "main"))


# ═══════════════════════════════════════════════════════════════
# Shutdown
# ═══════════════════════════════════════════════════════════════

class Test99_Cleanup(unittest.TestCase):
    """Clean up the shared server (runs last due to name ordering)."""

    def test_shutdown(self):
        _stop_shared_server()
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
