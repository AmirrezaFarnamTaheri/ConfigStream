"""
Honey Pot Detection Module.
Combines passive verification (VirusTotal) and active port scanning to identify malicious nodes.
"""

import asyncio
import logging
from typing import List
from configstream.security.virus_total import check_ip_reputation

logger = logging.getLogger(__name__)

# Ports that suggest a server is a generic VPS or Honeypot, not a dedicated proxy.
# 21: FTP
# 22: SSH (High risk of brute force logging)
# 23: Telnet (Legacy insecure)
HONEYPOT_PORTS = [21, 22, 23]


async def check_common_honeypot_ports(host: str, ports: List[int] = HONEYPOT_PORTS) -> bool:
    """
    Actively checks if common management ports are open.
    If a proxy server exposes Telnet or FTP, it is likely a honeypot or misconfigured.
    Returns True if any dangerous port is OPEN.
    """
    async def check_port(p: int) -> bool:
        try:
            # Very short timeout - we only care if it responds immediately
            conn = asyncio.open_connection(host, p)
            reader, writer = await asyncio.wait_for(conn, timeout=1.5)
            # If we connected, close immediately
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
        except Exception:
            return False

    # Check ports concurrently
    results = await asyncio.gather(*[check_port(p) for p in ports])
    if any(results):
        open_ports = [port for port, is_open in zip(ports, results) if is_open]
        logger.warning(f"Active Intel: Host {host} exposes dangerous ports: {open_ports}")
        return True

    return False


async def is_honeypot(host: str) -> bool:
    """
    Checks if the proxy host is a known honeypot or malicious IP.
    Uses a hybrid approach:
    1. Passive Intelligence (VirusTotal)
    2. Active Port Scanning (FTP/SSH/Telnet)
    """
    try:
        # 1. Active Port Check (Fastest to fail)
        if await check_common_honeypot_ports(host):
            return True

        # 2. Passive check via VirusTotal
        # If VT_API_KEY is missing, this returns {'malicious': 0} (Safe Fail-Open)
        report = await check_ip_reputation(host)

        if report.get("malicious", 0) > 0:
            logger.warning(
                f"Passive Intel: Host {host} flagged as malicious by VirusTotal."
            )
            return True

        return False
    except Exception as e:
        logger.error(f"Honeypot check failed for {host}: {e}")
        return (
            False  # Fail open on error to avoid blocking good proxies due to API errors
        )


async def check_traffic_interception(proxy_config: dict) -> bool:
    """
    Stub for traffic interception check.
    Kept for API compatibility.
    """
    return False
