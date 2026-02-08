import socket
import time
import requests
import logging
from typing import List, Dict, Any

# Setup local logger since importing from ..logging_config failed or was circular
logger = logging.getLogger(__name__)

class CensorshipLab:
    """
    Checks connectivity to sensitive sites to determine censorship status.
    """
    SENSITIVE_SITES = [
        "https://www.google.com",
        "https://www.facebook.com",
        "https://www.twitter.com",
        "https://www.youtube.com",
        "https://www.instagram.com",
        "https://www.wikipedia.org"
    ]

    def __init__(self):
        self.results = {}

    def check_connectivity(self, sites: List[str] = None) -> Dict[str, Any]:
        """
        Checks if sensitive sites are reachable.
        """
        target_sites = sites or self.SENSITIVE_SITES
        results = {}

        for site in target_sites:
            try:
                start_time = time.time()
                response = requests.get(site, timeout=5)
                latency = (time.time() - start_time) * 1000
                results[site] = {
                    "status": "reachable",
                    "code": response.status_code,
                    "latency_ms": round(latency, 2)
                }
                logger.info(f"Successfully connected to {site}")
            except requests.RequestException as e:
                results[site] = {
                    "status": "blocked",
                    "error": str(e)
                }
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
            "details": self.results
        }
