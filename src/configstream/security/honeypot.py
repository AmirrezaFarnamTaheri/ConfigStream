"""
Honey Pot Detection Module.
Uses passive verification (VirusTotal) instead of active scanning to avoid abuse complaints.
"""

import logging
import asyncio
from configstream.security.virus_total import check_ip_reputation

logger = logging.getLogger(__name__)

async def is_honeypot(host: str) -> bool:
    """
    Checks if the proxy host is a known honeypot or malicious IP using passive intelligence.
    Active port scanning is strictly prohibited on GitHub Actions to avoid IP bans.
    """
    try:
        # Passive check via VirusTotal
        # If VT_API_KEY is missing, this returns {'malicious': 0} (Safe Fail-Open for missing key)
        report = await check_ip_reputation(host)

        if report.get("malicious", 0) > 0:
            logger.warning(f"Passive Intel: Host {host} flagged as malicious by VirusTotal.")
            return True

        return False
    except Exception as e:
        logger.error(f"Honeypot check failed for {host}: {e}")
        return False  # Fail open on error to avoid blocking good proxies due to API errors


async def check_traffic_interception(proxy_config: dict) -> bool:
    """
    Stub for traffic interception check.
    Kept for API compatibility.
    """
    return False
