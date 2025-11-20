"""
VirusTotal Integration for Malware Scanning.
Validates domains/IPs against VirusTotal API if key is provided.
"""

import logging
import os
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

VT_API_KEY = os.getenv("VT_API_KEY")
VT_BASE_URL = "https://www.virustotal.com/api/v3"


class MalwareScanner:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or VT_API_KEY
        self.headers = {"x-apikey": self.api_key} if self.api_key else {}

    async def check_url(self, url: str) -> Dict[str, Any]:
        """
        Check a URL against VirusTotal.
        Returns simple dict with 'malicious', 'suspicious' counts.
        """
        if not self.api_key:
            return {"status": "skipped", "reason": "No API Key"}

        # For VT API v3, we need to base64 encode the URL
        import base64

        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")

        endpoint = f"{VT_BASE_URL}/urls/{url_id}"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(endpoint, headers=self.headers, timeout=10.0)

                if resp.status_code == 404:
                    # URL not found in VT, might need to scan it first (submission)
                    # For pipeline speed, we treat unknown as neutral/safe-ish
                    return {"status": "clean", "reason": "Not in VT db"}

                if resp.status_code == 200:
                    data = resp.json()
                    stats = (
                        data.get("data", {})
                        .get("attributes", {})
                        .get("last_analysis_stats", {})
                    )
                    malicious = stats.get("malicious", 0)
                    suspicious = stats.get("suspicious", 0)

                    if malicious > 0 or suspicious > 1:
                        return {
                            "status": "flagged",
                            "malicious": malicious,
                            "suspicious": suspicious,
                        }
                    return {"status": "clean"}

                logger.warning(f"VT API Error: {resp.status_code}")
                return {"status": "error", "code": resp.status_code}

        except Exception as e:
            logger.error(f"VT Scan Error: {e}")
            return {"status": "error", "error": str(e)}

    async def check_ip(self, ip: str) -> Dict[str, Any]:
        """Check an IP address."""
        if not self.api_key:
            return {"status": "skipped"}

        endpoint = f"{VT_BASE_URL}/ip_addresses/{ip}"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(endpoint, headers=self.headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    stats = (
                        data.get("data", {})
                        .get("attributes", {})
                        .get("last_analysis_stats", {})
                    )
                    malicious = stats.get("malicious", 0)
                    if malicious > 0:
                        return {"status": "flagged", "malicious": malicious}
                    return {"status": "clean"}
                return {"status": "error", "code": resp.status_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}
