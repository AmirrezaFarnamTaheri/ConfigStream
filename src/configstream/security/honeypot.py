# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Honey Pot Detection Module.
Combines passive verification (VirusTotal) to identify malicious nodes.
"""

import logging
from typing import List, Optional
from configstream.security.virus_total import check_ip_reputation

logger = logging.getLogger(__name__)


async def check_common_honeypot_ports(
    host: str, ports: Optional[List[int]] = None
) -> bool:
    """
    Active port scanning is DISABLED to comply with Zero-Budget / No-Abuse policy.
    Cloud providers flag this behavior as malicious.
    """
    return False


async def is_honeypot(host: str) -> bool:
    """
    Checks if the proxy host is a known honeypot or malicious IP.
    Uses only passive checks to ensure "Zero Abuse" policy.
    """
    try:
        # Passive check via VirusTotal
        report = await check_ip_reputation(host)

        # If VT_API_KEY is missing, the VirusTotal client returns
        # {'malicious': 0}. Surface this so operators know honeypot
        # intelligence is effectively disabled.
        if report.get("api_key_missing"):
            logger.warning(
                "VirusTotal API key not configured - honeypot reputation checks are disabled."
            )

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
