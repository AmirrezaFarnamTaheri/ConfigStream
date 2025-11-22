"""
Honey Pot Detection Module.
Uses passive verification (VirusTotal) instead of active scanning to avoid abuse complaints.
"""

import asyncio
import logging
from configstream.security.virus_total import check_ip_reputation

logger = logging.getLogger(__name__)


async def check_ports(host: str, ports=[21, 22, 23]) -> bool:
    """
    Checks if common honeypot ports are open.
    Uses a very short timeout to avoid stalling.
    """
    for port in ports:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=0.5
            )
            writer.close()
            await writer.wait_closed()
            logger.warning(f"Active Scan: Port {port} open on {host}. Possible Honeypot.")
            return True
        except Exception:
            pass
    return False


async def is_honeypot(host: str) -> bool:
    """
    Checks if the proxy host is a known honeypot or malicious IP.
    Combines passive intelligence (VirusTotal) and lightweight active port checks.
    """
    try:
        # 1. Active Port Check (Fastest)
        if await check_ports(host):
            return True

        # 2. Passive check via VirusTotal
        # If VT_API_KEY is missing, this returns {'malicious': 0} (Safe Fail-Open for missing key)
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
