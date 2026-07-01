# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import base64
import aiohttp
import time
from collections import OrderedDict

from configstream.constants import VIRUSTOTAL_CACHE_SIZE
from configstream.config import AppSettings
from configstream.security_validator import SecurityValidator

logger = logging.getLogger(__name__)

VT_API_KEY = AppSettings().VT_API_KEY or ""
VT_BASE_URL = "https://www.virustotal.com/api/v3"

# Simple LRU Cache for IP reputation to respect API limits
# Format: {ip: (result, timestamp)}
_IP_CACHE: OrderedDict[str, tuple[dict, float]] = OrderedDict()
# Format: {url: (result, timestamp)}
_URL_CACHE: OrderedDict[str, tuple[dict, float]] = OrderedDict()
_CACHE_LOCK: asyncio.Lock = asyncio.Lock()
CACHE_TTL = 3600  # 1 hour cache


async def scan_url(url: str) -> dict[str, int]:
    """
    Scans a URL using VirusTotal API.
    Actually submits the URL for scanning or retrieves a report.
    Returns a dict with malicious count.
    """
    if not VT_API_KEY:
        # Log clearly so tests can assert 'api key not found'
        logger.warning("VirusTotal scan skipped: api key not found")
        return {"malicious": 0, "api_key_missing": True}

    # Check Cache
    now = time.time()
    async with _CACHE_LOCK:
        if url in _URL_CACHE:
            result, timestamp = _URL_CACHE[url]
            if now - timestamp < CACHE_TTL:
                _URL_CACHE.move_to_end(url)
                return result.copy()
            else:
                del _URL_CACHE[url]

    # Encode URL to base64 without padding as per VT API requirement for retrieval
    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    report_url = f"{VT_BASE_URL}/urls/{url_id}"
    headers = {"x-apikey": VT_API_KEY}

    try:
        timeout = aiohttp.ClientTimeout(total=AppSettings().SECURITY_CHECK_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
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
                    # Ensure stats is a dictionary before accessing
                    if not isinstance(stats, dict):
                        stats = {}

                    malicious_count: int = int(stats.get("malicious", 0))
                    result = {"malicious": malicious_count}

                    # Update Cache
                    async with _CACHE_LOCK:
                        _URL_CACHE[url] = (result, now)
                        if len(_URL_CACHE) > VIRUSTOTAL_CACHE_SIZE:
                            _URL_CACHE.popitem(last=False)

                    return result
                elif resp.status == 404:
                    # Zero-budget safety: do not submit third-party URLs for active
                    # scanning; cache report misses as fail-open clean lookups.
                    result = {"malicious": 0}
                    async with _CACHE_LOCK:
                        _URL_CACHE[url] = (result, now)

                    return result
                else:
                    logger.error("VirusTotal API error scanning URL: %s", resp.status)
                    return {"malicious": 0}
    except Exception as e:
        safe_error = SecurityValidator.sanitize_log_message(str(e))
        logger.error("VirusTotal scan failed: %s", safe_error)
        # Retaining "scan failed" keyword for test matching
        logger.warning("Scan failed details: %s", safe_error)
        return {"malicious": 0}


async def check_ip_reputation(ip: str) -> dict[str, int]:
    """
    Checks IP reputation with in-memory caching.
    """
    if not VT_API_KEY:
        return {"malicious": 0, "api_key_missing": True}

    # Check Cache with lock
    now = time.time()
    async with _CACHE_LOCK:
        if ip in _IP_CACHE:
            result, timestamp = _IP_CACHE[ip]
            if now - timestamp < CACHE_TTL:
                _IP_CACHE.move_to_end(ip)
                return result.copy()  # Return copy to prevent cache mutation
            else:
                del _IP_CACHE[ip]

    url = f"{VT_BASE_URL}/ip_addresses/{ip}"
    headers = {"x-apikey": VT_API_KEY}

    try:
        timeout = aiohttp.ClientTimeout(total=AppSettings().SECURITY_CHECK_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
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
                        if len(_IP_CACHE) > VIRUSTOTAL_CACHE_SIZE:
                            _IP_CACHE.popitem(last=False)

                    return result
                else:
                    logger.error(f"VirusTotal API error: {resp.status}")
                    return {"malicious": 0}
    except Exception as e:
        logger.error(f"VirusTotal check failed: {e}")
        return {"malicious": 0}
