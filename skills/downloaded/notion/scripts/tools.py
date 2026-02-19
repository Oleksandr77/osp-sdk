"""
Notion Skill — OSP integration for Notion workspace.

Reads pages and databases from a Notion workspace via the Notion API v1.
Requires:
  NOTION_API_KEY — Notion integration token (secret_xxxx)

Setup:
  1. Go to https://www.notion.so/my-integrations
  2. Create a new integration, copy the Secret token
  3. Share the pages/databases you want to access with the integration
  4. Set: export NOTION_API_KEY="secret_xxxx"
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _get_api_key() -> Optional[str]:
    """Return Notion API key from environment."""
    key = os.environ.get("NOTION_API_KEY", "")
    if not key:
        logger.error("NOTION_API_KEY environment variable not set.")
    return key or None


def _notion_request(method: str, path: str, body: Optional[dict] = None) -> dict:
    """Make an authenticated request to the Notion API."""
    api_key = _get_api_key()
    if not api_key:
        return {"error": "NOTION_API_KEY not set. Set this env var to your Notion integration token."}

    url = f"{NOTION_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    data = json.dumps(body).encode("utf-8") if body else None
    req = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error("Notion API HTTP %s: %s", e.code, error_body)
        try:
            return {"error": json.loads(error_body)}
        except Exception:
            return {"error": f"HTTP {e.code}: {error_body}"}
    except URLError as e:
        logger.error("Notion API connection error: %s", e)
        return {"error": f"Connection error: {e.reason}"}


def search_pages(query: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    """Search pages and databases in the Notion workspace.

    Args:
        query: Text to search for. Empty string returns recent pages.
        limit: Max results to return (1–100).
    """
    body: dict = {"page_size": min(max(1, limit), 100)}
    if query:
        body["query"] = query
        body["filter"] = {"value": "page", "property": "object"}

    result = _notion_request("POST", "/search", body)
    if "error" in result:
        return [result]

    pages = []
    for item in result.get("results", []):
        title = _extract_title(item)
        pages.append({
            "id": item.get("id"),
            "type": item.get("object"),
            "title": title,
            "url": item.get("url"),
            "last_edited": item.get("last_edited_time"),
        })
    return pages


def get_page(page_id: str) -> Dict[str, Any]:
    """Get metadata and plain-text content of a Notion page.

    Args:
        page_id: Notion page ID (UUID with or without dashes).
    """
    page_id = page_id.replace("-", "")
    page = _notion_request("GET", f"/pages/{page_id}")
    if "error" in page:
        return page

    blocks = _notion_request("GET", f"/blocks/{page_id}/children")
    if "error" in blocks:
        return {"page": page, "content_error": blocks["error"]}

    content_lines = []
    for block in blocks.get("results", []):
        text = _extract_block_text(block)
        if text:
            content_lines.append(text)

    return {
        "id": page.get("id"),
        "title": _extract_title(page),
        "url": page.get("url"),
        "last_edited": page.get("last_edited_time"),
        "content": "\n".join(content_lines),
    }


def list_databases(limit: int = 20) -> List[Dict[str, Any]]:
    """List databases the integration has access to."""
    body = {
        "filter": {"value": "database", "property": "object"},
        "page_size": min(max(1, limit), 100),
    }
    result = _notion_request("POST", "/search", body)
    if "error" in result:
        return [result]

    databases = []
    for item in result.get("results", []):
        databases.append({
            "id": item.get("id"),
            "title": _extract_title(item),
            "url": item.get("url"),
            "last_edited": item.get("last_edited_time"),
        })
    return databases


def _extract_title(item: dict) -> str:
    """Extract a human-readable title from a Notion page or database object."""
    # Pages: properties.title.title[].plain_text
    props = item.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            parts = prop.get("title", [])
            return "".join(p.get("plain_text", "") for p in parts)
    # Databases: title[].plain_text
    title_parts = item.get("title", [])
    if title_parts:
        return "".join(p.get("plain_text", "") for p in title_parts)
    return "(Untitled)"


def _extract_block_text(block: dict) -> str:
    """Extract plain text from a Notion block."""
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})
    rich_text = block_data.get("rich_text", [])
    text = "".join(rt.get("plain_text", "") for rt in rich_text)

    # Add simple prefix for headings and bullets
    if block_type == "heading_1":
        return f"# {text}"
    elif block_type == "heading_2":
        return f"## {text}"
    elif block_type == "heading_3":
        return f"### {text}"
    elif block_type in ("bulleted_list_item", "numbered_list_item"):
        return f"• {text}"
    elif block_type == "code":
        lang = block_data.get("language", "")
        return f"```{lang}\n{text}\n```"
    elif block_type == "divider":
        return "---"
    return text


def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    OSP skill entry point for Notion integration.

    Supported actions (via 'action' argument):
      - 'search'    : Search pages/databases (args: query, limit)
      - 'get_page'  : Get page content (args: page_id)
      - 'list_databases': List databases (args: limit)

    Default action is 'search'.
    """
    action = arguments.get("action", "search")

    if action == "search":
        query = arguments.get("query", "")
        limit = int(arguments.get("limit", 10))
        results = search_pages(query=query, limit=limit)
        return {
            "action": "search",
            "query": query,
            "count": len(results),
            "results": results,
        }

    elif action == "get_page":
        page_id = arguments.get("page_id", "")
        if not page_id:
            return {"error": "Missing 'page_id' argument."}
        return get_page(page_id=page_id)

    elif action == "list_databases":
        limit = int(arguments.get("limit", 20))
        results = list_databases(limit=limit)
        return {
            "action": "list_databases",
            "count": len(results),
            "databases": results,
        }

    else:
        return {
            "error": f"Unknown action '{action}'. Use: search, get_page, list_databases."
        }