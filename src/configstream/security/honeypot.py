"""
Honey Pot Detection Module.
Actively probes proxies for suspicious behavior.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

SUSPICIOUS_PORTS = [22, 23, 25, 3389, 53]  # SSH, Telnet, SMTP, RDP, DNS


async def check_open_ports(host: str, timeout: float = 2.0) -> bool:
    """
    Check if the proxy host has suspicious open ports on itself.
    Many legitimate proxies are just open relays on hacked servers which might also expose other services.
    However, a 'Honey Pot' specifically might be logging everything.

    This function checks if the proxy IP *itself* exposes suspicious services.
    Returns True if suspicious ports are OPEN.
    """
    # This is a heuristic. Open SSH (22) is common on servers, so maybe not purely malicious,
    # but an open Telnet (23) is very suspicious.

    for port in SUSPICIOUS_PORTS:
        try:
            # Simple connect test
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            logger.warning(f"Suspicious port {port} open on {host}")
            return True
        except (OSError, asyncio.TimeoutError):
            continue

    return False


async def check_traffic_interception(proxy_config: dict) -> bool:
    """
    Simulate a check for traffic interception.
    In a real scenario, this would fetch a 'canary' URL over HTTP (not HTTPS)
    and check if the content is modified or if headers are injected.
    """
    # Placeholder for advanced logic
    # 1. Fetch http://neverssl.com via proxy
    # 2. Check hash of response
    # Since we don't have a live proxy connection context here easily without circular deps,
    # we'll implement the logic structure.
    return False


async def is_honeypot(host: str) -> bool:
    """
    Aggregate honeypot checks.
    """
    if await check_open_ports(host):
        return True
    return False
