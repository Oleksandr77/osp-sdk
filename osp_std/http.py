import requests
import socket
import ipaddress
from typing import Dict, Any, Optional
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

def _resolve_and_validate(url: str) -> str:
    """
    SSRF + DNS rebinding protection.
    Resolves hostname, validates IP, returns the first safe IP.
    The caller must pin the connection to this IP to prevent rebinding.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise PermissionError("No hostname in URL")

    # Step 1: Static deny list
    if hostname.lower() in DENY_DOMAINS:
        raise PermissionError(f"Access denied to restricted domain: {hostname}")

    # Step 2: DNS resolution — resolve and validate ALL returned IPs
    try:
        resolved_ips = socket.getaddrinfo(hostname, parsed.port or 443)
        safe_ip = None
        for family, _, _, _, sockaddr in resolved_ips:
            ip = sockaddr[0]
            if ip.lower() in DENY_DOMAINS or _is_private_ip(ip):
                raise PermissionError(
                    f"Access denied: {hostname} resolves to private IP {ip}"
                )
            if safe_ip is None:
                safe_ip = ip

        if safe_ip is None:
            raise PermissionError(f"No IP addresses resolved for {hostname}")

        return safe_ip
    except socket.gaierror:
        raise PermissionError(f"Cannot resolve hostname: {hostname}")

def _pin_to_ip(url: str, resolved_ip: str) -> str:
    """Replace hostname with resolved IP in URL to prevent DNS rebinding."""
    parsed = urlparse(url)
    # Replace hostname with IP, pass original host as Host header
    pinned_url = url.replace(f"://{parsed.hostname}", f"://{resolved_ip}", 1)
    return pinned_url

def get(url: str, params: Dict[str, Any] = None) -> str:
    resolved_ip = _resolve_and_validate(url)
    parsed = urlparse(url)
    pinned_url = _pin_to_ip(url, resolved_ip)
    resp = requests.get(
        pinned_url, params=params, timeout=10,
        headers={"Host": parsed.hostname},
        verify=True,
    )
    resp.raise_for_status()
    return resp.text

def post(url: str, json_data: Dict[str, Any] = None) -> str:
    resolved_ip = _resolve_and_validate(url)
    parsed = urlparse(url)
    pinned_url = _pin_to_ip(url, resolved_ip)
    resp = requests.post(
        pinned_url, json=json_data, timeout=10,
        headers={"Host": parsed.hostname},
        verify=True,
    )
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

