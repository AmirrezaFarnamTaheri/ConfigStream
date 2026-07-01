# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Honey Pot Detection Module.
Passive verification (VirusTotal) to identify malicious nodes.

Note: This module is not used in the main pipeline. The pipeline uses the Go
tester for honeypot checks. Port-based detection lives in security/blocklist.py
(HONEYPOT_PORTS / is_suspicious_port). is_honeypot is available for tests and
standalone/alternative use.
"""

import logging
from configstream.security.virus_total import check_ip_reputation
from configstream.security_validator import SecurityValidator

logger = logging.getLogger(__name__)


async def is_honeypot(host: str) -> bool:
    """
    Checks if the proxy host is a known honeypot or malicious IP.
    Uses only passive checks to ensure "Zero Abuse" policy.
    """
    try:
        report = await check_ip_reputation(host)
        safe_host = SecurityValidator.sanitize_log_message(host)

        if report.get("api_key_missing"):
            logger.warning(
                "VirusTotal API key not configured - honeypot reputation checks are disabled."
            )

        if report.get("malicious", 0) > 0:
            logger.warning(
                "Passive Intel: Host %s flagged as malicious by VirusTotal.",
                safe_host,
            )
            return True

        return False
    except Exception as e:
        logger.error(
            "Honeypot check failed for %s: %s",
            SecurityValidator.sanitize_log_message(host),
            SecurityValidator.sanitize_log_message(str(e)),
        )
        return False
