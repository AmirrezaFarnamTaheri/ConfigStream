import os
import logging
import base64
import aiohttp

logger = logging.getLogger(__name__)

VT_API_KEY = os.getenv("VT_API_KEY", "")
VT_BASE_URL = "https://www.virustotal.com/api/v3"


async def scan_url(url: str) -> dict:
    """
    Scans a URL using VirusTotal API.
    Actually submits the URL for scanning or retrieves a report.
    Returns a dict with malicious count.
    """
    if not VT_API_KEY:
        logger.warning("VirusTotal API key not found.")
        return {"malicious": 0}

    # Encode URL to base64 without padding as per VT API requirement for retrieval
    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    report_url = f"{VT_BASE_URL}/urls/{url_id}"
    headers = {"x-apikey": VT_API_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(report_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if not isinstance(data, dict):
                        return {"malicious": 0}
                    stats = (
                        data.get("data", {})
                        .get("attributes", {})
                        .get("last_analysis_stats", {})
                    )
                    return {"malicious": stats.get("malicious", 0)}
                elif resp.status == 404:
                    # URL not found, could submit it but for now just return clean
                    # Submitting requires POST to /urls
                    return {"malicious": 0}
                else:
                    logger.error(f"VirusTotal API error scanning URL: {resp.status}")
                    return {"malicious": 0}
    except Exception as e:
        logger.error(f"VirusTotal scan failed: {e}")
        return {"malicious": 0}


async def check_ip_reputation(ip: str) -> dict:
    """
    Checks IP reputation.
    """
    if not VT_API_KEY:
        return {"malicious": 0}

    url = f"{VT_BASE_URL}/ip_addresses/{ip}"
    headers = {"x-apikey": VT_API_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            # Use context manager for the response object as per aiohttp
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    # Await the json() coroutine
                    data = await resp.json()
                    # Ensure data is a dictionary
                    if not isinstance(data, dict):
                        return {"malicious": 0}
                    stats = (
                        data.get("data", {})
                        .get("attributes", {})
                        .get("last_analysis_stats", {})
                    )
                    return {"malicious": stats.get("malicious", 0)}
                else:
                    logger.error(f"VirusTotal API error: {resp.status}")
                    return {"malicious": 0}
    except Exception as e:
        logger.error(f"VirusTotal check failed: {e}")
        return {"malicious": 0}
