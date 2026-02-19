import os
import glob
from typing import List, Union

# Sandbox Configuration
# Lazy evaluation via env var or CWD at first access
_sandbox_root = None

def _get_sandbox_root():
    global _sandbox_root
    if _sandbox_root is None:
        _sandbox_root = os.path.realpath(os.environ.get("OSP_SANDBOX_ROOT", os.getcwd()))
    return _sandbox_root

def _ensure_sandboxed(path: str) -> str:
    """
    Ensures the path is within the sandbox root.
    Uses realpath to resolve symlinks and prevent sandbox escape.
    Returns the absolute path if safe, raises PermissionError otherwise.
    """
    sandbox = _get_sandbox_root()
    # Resolve symlinks to prevent escape via symlink traversal
    abs_path = os.path.realpath(os.path.join(sandbox, path))
    
    # Check if it starts with sandbox root
    if not abs_path.startswith(sandbox + os.sep) and abs_path != sandbox:
        raise PermissionError(f"Access denied: Path '{path}' escapes sandbox root '{sandbox}'")
    
    return abs_path

def read_file(path: str) -> str:
    """
    Reads the content of a file (UTF-8).
    """
    safe_path = _ensure_sandboxed(path)
    if not os.path.exists(safe_path):
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(safe_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path: str, content: str) -> str:
    """
    Writes content to a file. Overwrites if exists.
    """
    safe_path = _ensure_sandboxed(path)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(safe_path), exist_ok=True)
    
    with open(safe_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    return f"Successfully wrote {len(content)} bytes to {path}"

def list_dir(path: str = ".") -> List[str]:
    """
    Lists entries in a directory.
    """
    safe_path = _ensure_sandboxed(path)
    if not os.path.exists(safe_path):
        raise FileNotFoundError(f"Directory not found: {path}")
        
    return os.listdir(safe_path)

# OSP Export
def execute(args: dict):
    """
    Dispatcher for OSP Agent execution.
    """
    command = args.get("command")
    if command == "read_file":
        return read_file(args.get("path"))
    elif command == "write_file":
        return write_file(args.get("path"), args.get("content"))
    elif command == "list_dir":
        return list_dir(args.get("path", "."))
    else:
        raise ValueError(f"Unknown command: {command}")
