# SPDX-License-Identifier: AGPL-3.0-or-later
import time
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class CensorshipLab:
    """
    Checks connectivity to sensitive sites to determine censorship status.
    Uses async httpx to comply with the project's no-blocking-IO rule.
    """

    SENSITIVE_SITES = [
        "https://www.google.com",
        "https://www.facebook.com",
        "https://www.twitter.com",
        "https://www.youtube.com",
        "https://www.instagram.com",
        "https://www.wikipedia.org",
    ]

    def __init__(self) -> None:
        self.results: Dict[str, Any] = {}

    async def check_connectivity(
        self, sites: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Checks if sensitive sites are reachable (async).
        """
        target_sites = sites or self.SENSITIVE_SITES
        results: Dict[str, Any] = {}

        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, trust_env=False) as client:
            for site in target_sites:
                try:
                    start_time = time.monotonic()
                    response = await client.get(site)
                    latency = (time.monotonic() - start_time) * 1000
                    results[site] = {
                        "status": "reachable",
                        "code": response.status_code,
                        "latency_ms": round(latency, 2),
                    }
                    logger.info(f"Successfully connected to {site}")
                except httpx.HTTPError as e:
                    results[site] = {"status": "blocked", "error": str(e)}
                    logger.warning(f"Failed to connect to {site}: {e}")

        self.results = results
        return results

    def get_censorship_report(self) -> Dict[str, Any]:
        """Returns a summary report of censorship status."""
        total = len(self.results)
        if total == 0:
            return {"status": "unknown", "details": "No checks run"}

        blocked = sum(1 for r in self.results.values() if r["status"] == "blocked")
        score = 100 - (blocked / total * 100)

        status = "Open"
        if score < 50:
            status = "Heavy Censorship"
        elif score < 90:
            status = "Moderate Censorship"

        return {
            "censorship_score": round(score, 2),
            "status": status,
            "blocked_count": blocked,
            "total_sites": total,
            "details": self.results,
        }
