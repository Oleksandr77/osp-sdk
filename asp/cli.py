"""
ASP CLI — Command-line interface for Open Skills Protocol
===========================================================
Usage::

    asp dev hello.py          # Start dev server with hot-reload
    asp init                  # Scaffold a new ASP project  
    asp skills hello.py       # List skills in a file
    asp test                  # Run conformance tests
"""

import sys
import os
import time
import importlib
import importlib.util
import argparse


def _load_skill_file(filepath: str):
    """Import a Python file to register its @skill decorators."""
    if not os.path.isfile(filepath):
        print(f"\033[91m✗ File not found: {filepath}\033[0m")
        sys.exit(1)

    # Add the file's directory to sys.path for local imports
    file_dir = os.path.dirname(os.path.abspath(filepath))
    if file_dir not in sys.path:
        sys.path.insert(0, file_dir)

    spec = importlib.util.spec_from_file_location("_asp_skills", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cmd_dev(args):
    """Start development server with auto-reload."""
    filepath = args.file
    port = args.port
    host = args.host

    print(f"\033[95m⚡ OSP Dev Server (ASP Adapter)\033[0m")
    print(f"\033[90m{'─' * 40}\033[0m")

    # Set dev mode
    os.environ["ASP_MODE"] = "dev"

    # Load the skill file
    _load_skill_file(filepath)

    from asp.decorators import get_registered_skills
    skills = get_registered_skills()

    if not skills:
        print(f"\033[93m⚠ No @skill decorators found in {filepath}\033[0m")
        print(f"  Add skills like:")
        print(f"    from asp import skill")
        print(f"    @skill('my_skill', description='...')")
        print(f"    def my_skill(): ...")
        sys.exit(1)

    print(f"  📂 Loaded: \033[96m{filepath}\033[0m")
    print(f"  🔧 Skills: \033[93m{len(skills)}\033[0m")

    # Start server
    from asp.server import serve
    serve(host=host, port=port, dev_mode=True)


def cmd_init(args):
    """Scaffold a new ASP project."""
    project_name = args.name or "my-asp-app"
    project_dir = os.path.join(os.getcwd(), project_name)

    if os.path.exists(project_dir):
        print(f"\033[91m✗ Directory already exists: {project_dir}\033[0m")
        sys.exit(1)

    os.makedirs(project_dir)

    # Create main.py
    main_py = '''"""
My OSP Application
==================
Start with: asp dev main.py
"""
from asp import skill, serve


@skill("greet", description="Say hello to someone", keywords=["hello", "greet", "hi"])
def greet(name: str = "World") -> str:
    """Greet someone by name."""
    return f"Hello, {name}! Welcome to ASP."


@skill("calculator", description="Perform calculations", keywords=["math", "calc", "calculate"])
def calculator(expression: str) -> str:
    """Evaluate a math expression safely."""
    allowed = set("0123456789+-*/.()")
    if not all(c in allowed or c == ' ' for c in expression):
        return "Error: only basic math operations are allowed"
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    serve()
'''

    readme = f"""# {project_name}

Built with **Open Skills Protocol (OSP)**.

## Quick Start

```bash
pip install asp-sdk
asp dev main.py
```

Then open http://localhost:8080/_dashboard
"""

    with open(os.path.join(project_dir, "main.py"), "w") as f:
        f.write(main_py)

    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write(readme)

    print(f"\033[92m✓ Created project: {project_name}/\033[0m")
    print(f"  📄 main.py — 2 example skills")
    print(f"  📖 README.md")
    print(f"\n  Next steps:")
    print(f"    cd {project_name}")
    print(f"    asp dev main.py")


def cmd_skills(args):
    """List skills in a file."""
    _load_skill_file(args.file)
    from asp.decorators import get_registered_skills
    skills = get_registered_skills()

    if not skills:
        print("No skills found.")
        return

    print(f"\n\033[95m⚡ OSP Skills ({len(skills)})\033[0m\n")

    for s in skills.values():
        kw = ", ".join(s.keywords[:5]) if s.keywords else "—"
        print(f"  \033[96m{s.skill_id}\033[0m")
        print(f"    {s.description}")
        print(f"    Keywords: {kw}")
        print(f"    Risk: {s.risk_level} | Version: v{s.version}")
        print(f"    Params: {', '.join(s.parameters.keys()) or 'none'}")
        print()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="asp",
        description="⚡ Open Skills Protocol — AI skill routing made simple",
    )
    parser.add_argument("--version", action="version", version="asp-sdk 0.1.0")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # asp dev
    dev_parser = subparsers.add_parser("dev", help="Start development server")
    dev_parser.add_argument("file", help="Python file with @skill decorators")
    dev_parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    dev_parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")

    # asp init
    init_parser = subparsers.add_parser("init", help="Scaffold a new ASP project")
    init_parser.add_argument("name", nargs="?", default=None, help="Project name")

    # asp skills
    skills_parser = subparsers.add_parser("skills", help="List skills in a file")
    skills_parser.add_argument("file", help="Python file with @skill decorators")

    args = parser.parse_args()

    if args.command == "dev":
        cmd_dev(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "skills":
        cmd_skills(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
