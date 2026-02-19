import platform
import datetime
import os

def get_time() -> str:
    return datetime.datetime.now().isoformat()

def get_platform_info() -> dict:
    return {
        "system": platform.system(),           # "Linux" / "Darwin" / "Windows"
        "python_version": platform.python_version()
        # Intentionally omitted: release, version, processor (fingerprinting risk)
    }

# OSP Export
def execute(args: dict):
    command = args.get("command")
    if command == "get_time":
        return get_time()
    elif command == "get_platform_info":
        return get_platform_info()
    else:
        raise ValueError(f"Unknown command: {command}")
