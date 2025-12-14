"""
Scrapes Warp configurations from public repositories and endpoints.
"""

import logging
import json
import re
import base64
from typing import List, Dict, Any, Optional

from ...models import Proxy
from ...fetcher import Fetcher
from .utils import make_entry

logger = logging.getLogger(__name__)

# Regex to find hidden WireGuard configs in non-JSON text
# Captures PrivateKey and Address (optional port)
# Format: PrivateKey = <key> ... Address = <ip>
WIREGUARD_REGEX = re.compile(
    r"PrivateKey\s*=\s*([a-zA-Z0-9+/]{43,44}=)[\s\S]*?Address\s*=\s*([0-9a-f:./]+)",
    re.IGNORECASE,
)

WARP_SOURCES = [
    {
        "name": "blue-music/blue-music-warp",
        "url": "https://raw.githubusercontent.com/blue-music/blue-music-warp/master/warp.json",
        "kind": "singbox",
        "max_entries": 50,
    },
    {
        "name": "yebekhe/TelegramV2rayCollector/warp",
        "url": "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/warp",
        "kind": "text_decode",  # New kind for encoded links
        "max_entries": 100,
    },
    {
        "name": "vvb2060/warp-endpoint",
        "url": "https://raw.githubusercontent.com/vvb2060/warp-endpoint/main/clean_ip.txt",
        "kind": "endpoint_list",  # Just IPs
        "max_entries": 50,
    },
    # Original sources can be kept here if they are still valid
]


class WarpScraper:
    def __init__(self):
        self.fetcher = Fetcher()

    async def scrape_warp_sources(self) -> List[Proxy]:
        """
        Iterates through known WARP sources and extracts credentials.
        """
        all_proxies = []

        for source in WARP_SOURCES:
            name = source["name"]
            url = source["url"]
            kind = source["kind"]
            max_entries = source.get("max_entries", 20)

            try:
                content = await self.fetcher.fetch_text(url)
                if not content:
                    continue

                entries: List[Proxy] = []

                if kind == "singbox":
                    try:
                        data = json.loads(content)
                        # Singbox outbound format
                        outbounds = data.get("outbounds", [])
                        for out in outbounds:
                            if out.get("type") == "wireguard":
                                # Extract credentials
                                priv = out.get("private_key")
                                addr = out.get("local_address", ["172.16.0.2/32"])
                                if isinstance(addr, list):
                                    addr = addr[0]

                                # Use make_entry helper if available, or manual Proxy creation
                                entry = make_entry(
                                    "scraped-sb", priv, "auto", None, [0, 0, 0]
                                )
                                if entry:
                                    entries.append(entry)
                    except json.JSONDecodeError:
                        logger.debug(f"Failed to parse JSON from {name}")

                elif kind == "text_decode":
                    # Handle base64 encoded warp:// links or config blocks
                    try:
                        # Attempt Base64 decode first
                        decoded = ""
                        try:
                            decoded = base64.b64decode(content).decode(
                                "utf-8", errors="ignore"
                            )
                        except Exception:
                            decoded = content

                        for line in decoded.splitlines():
                            line = line.strip()
                            if line.startswith("warp://"):
                                # Parse custom URI scheme (conceptual)
                                # warp://key@host:port?peer=...
                                pass
                            elif "PrivateKey" in line:
                                # Might be a raw config block
                                pass
                    except Exception:
                        pass

                elif kind == "endpoint_list":
                    # Just scrape IPs for the clean IP pool, not full identities
                    # This would ideally feed into ProxyWasher.clean_ips directly
                    # For now, we log or return a special "EndpointOnly" proxy if architecture allows
                    pass

                # Fallback: Regex Scan
                # If specialized parsers yielded nothing, try brute-force regex on raw content
                if not entries:
                    matches = WIREGUARD_REGEX.findall(content)
                    for priv_key, address in matches:
                        # Address usually comes as "172.16.0.2/32" or just IP
                        clean_addr = address.split("/")[0].strip()
                        entry = make_entry(
                            "scraped-regex", priv_key, "auto", None, [0, 0, 0]
                        )
                        if entry:
                            entries.append(entry)

                # Limit and Add
                if entries:
                    limited = entries[:max_entries]
                    all_proxies.extend(limited)
                    logger.info(f"Scraped {len(limited)} WARP configs from {name}")

            except Exception as e:
                logger.debug(f"Failed to scrape {name}: {e}")

        return all_proxies
