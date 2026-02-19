import requests
import socket
import ipaddress
from typing import Dict, Any
from urllib.parse import urlparse

# Security: SSRF Protection — deny all private/reserved IP ranges
DENY_DOMAINS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1"}

def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP is in any private/reserved range (RFC 1918, link-local, etc.)."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        )
    except ValueError:
        return False

def _check_domain(url: str):
    """SSRF protection: blocks requests to private networks and cloud metadata."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise PermissionError("No hostname in URL")

    # Step 1: Static deny list
    if hostname.lower() in DENY_DOMAINS:
        raise PermissionError(f"Access denied to restricted domain: {hostname}")

    # Step 2: DNS resolution check — resolve hostname and verify it's not private
    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in resolved_ips:
            ip = sockaddr[0]
            if ip.lower() in DENY_DOMAINS or _is_private_ip(ip):
                raise PermissionError(
                    f"Access denied: {hostname} resolves to private IP {ip}"
                )
    except socket.gaierror:
        # Can't resolve — block (fail-closed)
        raise PermissionError(f"Cannot resolve hostname: {hostname}")

def get(url: str, params: Dict[str, Any] = None) -> str:
    _check_domain(url)
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.text

def post(url: str, json_data: Dict[str, Any] = None) -> str:
    _check_domain(url)
    resp = requests.post(url, json=json_data, timeout=10)
    resp.raise_for_status()
    return resp.text

# OSP Export
def execute(args: dict):
    command = args.get("command")
    if command == "get":
        return get(args.get("url"), args.get("params"))
    elif command == "post":
        return post(args.get("url"), args.get("json"))
    else:
        raise ValueError(f"Unknown command: {command}")

