"""
ASP @skill Decorator
=====================
Transform any Python function into an ASP skill with a single decorator.

Usage::

    from asp import skill

    @skill("calculator", description="Perform math operations", keywords=["math", "calc"])
    def calculator(expression: str) -> str:
        return str(eval(expression))

    # Access skill metadata
    print(calculator.skill_id)       # "calculator"
    print(calculator.description)    # "Perform math operations"
    print(calculator.to_manifest())  # Full ASP manifest dict
"""

import inspect
import functools
from typing import Any, Callable, Dict, List, Optional


# Global registry of all decorated skills
_SKILL_REGISTRY: Dict[str, "SkillWrapper"] = {}


class SkillWrapper:
    """Wraps a Python function as an ASP skill with metadata and manifest generation."""

    def __init__(
        self,
        func: Callable,
        skill_id: str,
        description: str = "",
        keywords: Optional[List[str]] = None,
        risk_level: str = "LOW",
        version: str = "1.0.0",
        security: Optional[str] = None,
    ):
        self._func = func
        self.skill_id = skill_id
        self.description = description or func.__doc__ or ""
        self.keywords = keywords or []
        self.risk_level = risk_level
        self.version = version
        self.security = security

        # Extract parameter info from function signature
        sig = inspect.signature(func)
        self.parameters = {}
        for name, param in sig.items() if hasattr(sig, 'items') else sig.parameters.items():
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                type_map = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}
                param_type = type_map.get(param.annotation, "string")
            self.parameters[name] = {
                "type": param_type,
                "required": param.default == inspect.Parameter.empty,
            }

        # Preserve original function metadata
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs) -> Any:
        """Execute the skill function."""
        return self._func(*args, **kwargs)

    def to_manifest(self) -> Dict[str, Any]:
        """Generate ASP-compliant skill manifest."""
        return {
            "skill_id": self.skill_id,
            "name": self.skill_id.replace("_", " ").replace("-", " ").title(),
            "description": self.description,
            "version": self.version,
            "activation_keywords": self.keywords,
            "risk_level": self.risk_level,
            "parameters": self.parameters,
            "security": self.security,
            "protocol": "ASP/1.0",
        }

    def to_candidate(self) -> Dict[str, Any]:
        """Generate a candidate dict for routing."""
        return {
            "skill_id": self.skill_id,
            "skill_ref": self.skill_id,
            "name": self.skill_id.replace("_", " ").replace("-", " ").title(),
            "description": self.description,
            "activation_keywords": self.keywords,
            "risk_level": self.risk_level,
            "safety_clearance": "allow",
        }

    def __repr__(self) -> str:
        return f"<ASPSkill '{self.skill_id}' v{self.version}>"


def skill(
    skill_id: str,
    description: str = "",
    keywords: Optional[List[str]] = None,
    risk_level: str = "LOW",
    version: str = "1.0.0",
    security: Optional[str] = None,
) -> Callable:
    """
    Decorator to register a Python function as an ASP skill.

    Args:
        skill_id: Unique identifier for the skill
        description: Human-readable description (used for routing)
        keywords: Activation keywords for BM25 scoring
        risk_level: Risk level (LOW, MEDIUM, HIGH, CRITICAL)
        version: Semantic version string
        security: Security profile (e.g., "PCI_DSS")

    Returns:
        SkillWrapper that preserves the original function behavior

    Example::

        @skill("weather", description="Get weather data", keywords=["weather", "forecast"])
        def get_weather(city: str) -> str:
            return f"Weather in {city}: Sunny, 22°C"
    """
    def decorator(func: Callable) -> SkillWrapper:
        wrapper = SkillWrapper(
            func=func,
            skill_id=skill_id,
            description=description,
            keywords=keywords,
            risk_level=risk_level,
            version=version,
            security=security,
        )
        _SKILL_REGISTRY[skill_id] = wrapper
        return wrapper

    return decorator


def get_registered_skills() -> Dict[str, SkillWrapper]:
    """Return all registered skills."""
    return dict(_SKILL_REGISTRY)


def clear_registry():
    """Clear the skill registry (useful for testing)."""
    _SKILL_REGISTRY.clear()
