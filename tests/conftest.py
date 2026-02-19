"""
Shared Test Fixtures (conftest.py)
===================================
Provides reusable fixtures for all OSP test modules.
Eliminates boilerplate and ensures consistent test setup.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)


# ──────────────────────────────────────────────────────
# Service Factories
# ──────────────────────────────────────────────────────

def make_router():
    """Create a fresh RouterService instance."""
    from osp_server.logic.routing import RouterService
    return RouterService()


def make_safety():
    """Create a fresh SafetyService instance."""
    from osp_server.logic.safety import SafetyService
    return SafetyService()


def make_skill_manager(skills_dir=None):
    """Create a SkillManager pointing at the real skills directory."""
    from ai_core.skill_manager import SkillManager
    if skills_dir is None:
        skills_dir = os.path.join(PROJECT_ROOT, "skills")
    return SkillManager(skills_dir=skills_dir)


def make_degradation_controller():
    """Create a DegradationController in D0 (normal) state."""
    from osp_server.logic.degradation import DegradationController, DegradationLevel
    ctrl = DegradationController()
    ctrl.set_level(DegradationLevel.D0_NORMAL)
    return ctrl


# ──────────────────────────────────────────────────────
# Mock Candidates
# ──────────────────────────────────────────────────────

MOCK_CANDIDATES = {
    "calendar": {
        "skill_id": "org.test.calendar",
        "name": "Calendar Scheduler",
        "description": "Schedule meetings, events, and appointments",
        "activation_keywords": ["schedule", "meeting", "event", "calendar"],
        "risk_level": "LOW",
    },
    "weather": {
        "skill_id": "org.test.weather",
        "name": "Weather Forecast",
        "description": "Get weather forecast, rain, temperature, sun",
        "activation_keywords": ["weather", "forecast", "rain", "temperature"],
        "risk_level": "LOW",
    },
    "finance": {
        "skill_id": "org.test.finance",
        "name": "Financial Reports",
        "description": "Quarterly earnings, sales trends, revenue analysis",
        "activation_keywords": ["earnings", "revenue", "quarterly", "finance"],
        "risk_level": "MEDIUM",
    },
    "admin": {
        "skill_id": "org.example.admin.system_handler",
        "name": "Admin System Handler",
        "description": "Manage system settings and configuration",
        "activation_keywords": ["admin", "system", "manage", "config"],
        "risk_level": "HIGH",
    },
    "storage": {
        "skill_id": "org.example.storage.file_organizer",
        "name": "Storage File Organizer",
        "description": "Organize files and storage management",
        "activation_keywords": ["organize", "files", "storage"],
        "risk_level": "LOW",
    },
}


def get_candidates(*names):
    """Get a list of mock candidates by short name."""
    return [MOCK_CANDIDATES[n] for n in names if n in MOCK_CANDIDATES]


# ──────────────────────────────────────────────────────
# Test App Client (for integration tests)
# ──────────────────────────────────────────────────────

def make_test_client():
    """Create a FastAPI TestClient for server.py (requires httpx)."""
    try:
        from fastapi.testclient import TestClient
        from osp_server.server import app
        return TestClient(app)
    except ImportError:
        return None


# ──────────────────────────────────────────────────────
# Environment Detection
# ──────────────────────────────────────────────────────

def is_ci():
    """Returns True if running in CI environment."""
    return os.environ.get("CI", "").lower() in ("true", "1", "yes")


def has_module(name):
    """Check if a Python module is available."""
    try:
        __import__(name)
        return True
    except ImportError:
        return False


HAS_PYDANTIC = has_module("pydantic")
HAS_SKLEARN = has_module("sklearn")
HAS_SENTENCE_TRANSFORMERS = has_module("sentence_transformers")
HAS_FASTAPI = has_module("fastapi")
HAS_PSUTIL = has_module("psutil")
