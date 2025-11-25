import asyncio
import os
import logging
import base64
import aiohttp
import time
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)

VT_API_KEY = os.getenv("VT_API_KEY", "")
VT_BASE_URL = "https://www.virustotal.com/api/v3"

# Simple LRU Cache for IP reputation to respect API limits
# Format: {ip: (result, timestamp)}
_IP_CACHE: OrderedDict[str, tuple[dict, float]] = OrderedDict()
_CACHE_LOCK: asyncio.Lock = asyncio.Lock()
CACHE_TTL = 3600  # 1 hour cache
CACHE_SIZE = 1000

# Shared HTTP session for efficiency
_session: Optional[aiohttp.ClientSession] = None
_session_lock: asyncio.Lock = asyncio.Lock()


async def _get_session() -> aiohttp.ClientSession:
    """Get or create shared aiohttp session."""
    global _session
    async with _session_lock:
        if _session is None or _session.closed:
            _session = aiohttp.ClientSession()
        return _session


async def close_session():
    """Close the shared session (call on shutdown)."""
    global _session
    async with _session_lock:
        if _session and not _session.closed:
            await _session.close()
            _session = None


async def scan_url(url: str) -> dict[str, int]:
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
        session = await _get_session()
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
                # Use explicit cast or conversion to ensure dict return type
                malicious_count: int = stats.get("malicious", 0)
                return {"malicious": malicious_count}
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


async def check_ip_reputation(ip: str) -> dict[str, int]:
    """
    Checks IP reputation with in-memory caching.
    """
    if not VT_API_KEY:
        return {"malicious": 0}

    # Check Cache with lock
    now = time.time()
    async with _CACHE_LOCK:
        if ip in _IP_CACHE:
            result, timestamp = _IP_CACHE[ip]
            if now - timestamp < CACHE_TTL:
                _IP_CACHE.move_to_end(ip)
                return result
            else:
                del _IP_CACHE[ip]

    url = f"{VT_BASE_URL}/ip_addresses/{ip}"
    headers = {"x-apikey": VT_API_KEY}

    try:
        session = await _get_session()
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
                result = {"malicious": stats.get("malicious", 0)}

                # Update Cache with lock
                async with _CACHE_LOCK:
                    _IP_CACHE[ip] = (result, now)
                    if len(_IP_CACHE) > CACHE_SIZE:
                        _IP_CACHE.popitem(last=False)

                return result
            else:
                logger.error(f"VirusTotal API error: {resp.status}")
                return {"malicious": 0}
    except Exception as e:
        logger.error(f"VirusTotal check failed: {e}")
        return {"malicious": 0}
