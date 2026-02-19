"""
Open Skills Protocol (OSP) SDK
================================
Build AI skills in 3 lines. Intelligent routing, built-in safety, zero config.

Quick Start::

    from asp import skill, serve

    @skill("greet", description="Say hello to someone")
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    serve()
"""

__version__ = "0.1.0"
__protocol__ = "Open Skills Protocol"
__abbreviation__ = "OSP"

from asp.decorators import skill
from asp.server import serve, ASPServer
from asp.client import ASPClient

__all__ = [
    "skill",
    "serve",
    "ASPServer",
    "ASPClient",
    "__version__",
    "__protocol__",
]
