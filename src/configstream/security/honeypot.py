# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Honey Pot Detection Module.
Passive verification (VirusTotal) to identify malicious nodes.

Note: This module is not used in the main pipeline. Port-based honeypot
detection lives in security/blocklist.py (HONEYPOT_PORTS / is_suspicious_port).
"""

import logging
from configstream.security.virus_total import check_ip_reputation

logger = logging.getLogger(__name__)


async def is_honeypot(host: str) -> bool:
    """
    Checks if the proxy host is a known honeypot or malicious IP.
    Uses only passive checks to ensure "Zero Abuse" policy.
    """
    try:
        report = await check_ip_reputation(host)

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
        return False
