"""
ASP Hello World — The simplest possible ASP example
=====================================================
Start with: asp dev hello.py (or python hello.py)
"""
from asp import skill, serve


@skill("greet", description="Say hello to someone", keywords=["hello", "greet", "hi"])
def greet(name: str = "World") -> str:
    """Greet someone by name."""
    return f"Hello, {name}! 👋"


@skill("calculator", description="Perform math calculations", keywords=["math", "calc", "calculate", "sum"])
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    allowed = set("0123456789+-*/.()")
    if not all(c in allowed or c == ' ' for c in expression):
        return "Error: only basic math operations allowed"
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"


@skill("echo", description="Echo back the input", keywords=["echo", "repeat", "say"])
def echo(text: str) -> str:
    """Echo the input text."""
    return f"🔊 {text}"


if __name__ == "__main__":
    serve()
