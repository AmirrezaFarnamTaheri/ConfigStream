# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Scrapes Warp configurations from public repositories and endpoints.
"""

import logging
import json
import re
import base64
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs

import httpx

from configstream.models import Proxy
from configstream.intelligence.washer.utils import make_entry
from configstream.security_validator import SecurityValidator

logger = logging.getLogger(__name__)

# Regex to find hidden WireGuard configs in non-JSON text
# Captures PrivateKey and Address (optional port)
# Format: PrivateKey = <key> ... Address = <ip>
WIREGUARD_REGEX = re.compile(
    r"PrivateKey\s*=\s*([a-zA-Z0-9+/]{43,44}=)[\s\S]*?Address\s*=\s*([0-9a-f:./]+)",
    re.IGNORECASE,
)

# Regex for extracting just PrivateKey from a line
PRIVATEKEY_LINE_REGEX = re.compile(
    r"PrivateKey\s*=\s*([a-zA-Z0-9+/]{43,44}=)", re.IGNORECASE
)

# Regex for valid IPv4/IPv6 addresses (for endpoint list)
IP_REGEX = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    r"|^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
)

# Updated Sources (Removed dead links, added more reliable ones if possible)
WARP_SOURCES: List[Dict[str, Any]] = [
    {
        "name": "ircfspace/warpendpoint",
        "url": "https://raw.githubusercontent.com/ircfspace/warpendpoint/main/result/warp-ip.txt",
        "kind": "endpoint_list",
        "max_entries": 100,
    },
    # Many public WARP key repos are transient. We rely on KeyGenerator if these fail.
]


class WarpScraper:
    def __init__(self) -> None:
        self._timeout = 30.0
        # Collected clean endpoint IPs (can be used by ProxyWasher)
        self.scraped_endpoints: List[str] = []

    def _parse_warp_uri(self, uri: str) -> Proxy | None:
        """
        Parse warp:// URI scheme.
        Format: warp://privatekey@host:port?peer=pubkey&reserved=0,0,0
        """
        try:
            # Remove warp:// prefix
            if not uri.startswith("warp://"):
                return None

            # Parse as URL (warp:// -> http:// for parsing)
            parsed = urlparse(uri.replace("warp://", "http://"))

            # Extract private key from username portion
            private_key = parsed.username
            if not private_key or len(private_key) < 40:
                return None

            # Extract host and port
            host = parsed.hostname or "auto"
            port = parsed.port or 2408

            # Parse query parameters
            params = parse_qs(parsed.query)
            peer_pub = params.get("peer", [None])[0]

            # Parse reserved bytes
            reserved = [0, 0, 0]
            if "reserved" in params:
                try:
                    reserved = [int(x) for x in params["reserved"][0].split(",")][:3]
                except (ValueError, IndexError):
                    reserved = [0, 0, 0]

            return make_entry("warp-uri", private_key, host, peer_pub, reserved, port)

        except Exception as e:
            safe_e = SecurityValidator.sanitize_log_message(str(e))
            logger.debug(f"Failed to parse warp:// URI: {safe_e}")
            return None

    def _extract_from_config_block(self, text: str) -> List[Proxy]:
        """
        Extract WireGuard credentials from raw config block text.
        Handles multi-line WireGuard config format.
        """
        entries = []

        # Find all PrivateKey matches in the text
        matches = PRIVATEKEY_LINE_REGEX.findall(text)
        for private_key in matches:
            entry = make_entry("config-block", private_key, "auto", None, [0, 0, 0])
            if entry:
                entries.append(entry)

        return entries

    async def scrape_warp_sources(self) -> List[Proxy]:
        """
        Iterates through known WARP sources and extracts credentials.
        """
        all_proxies = []
        self.scraped_endpoints = []  # Reset endpoints on each scrape

        for source in WARP_SOURCES:
            name = source["name"]
            url = source["url"]
            kind = source["kind"]
            max_entries_raw = source.get("max_entries", 20)
            max_entries: int = (
                max_entries_raw if isinstance(max_entries_raw, int) else 20
            )

            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout, follow_redirects=True, trust_env=False
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                content = resp.text
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

                        config_block_lines = []
                        for line in decoded.splitlines():
                            line = line.strip()
                            if line.startswith("warp://"):
                                # Parse warp:// URI scheme
                                entry = self._parse_warp_uri(line)
                                if entry:
                                    entries.append(entry)
                            elif "PrivateKey" in line or "[Interface]" in line:
                                # Accumulate potential config block lines
                                config_block_lines.append(line)
                            elif config_block_lines and line:
                                # Continue accumulating if we're in a config block
                                config_block_lines.append(line)

                        # Process accumulated config block
                        if config_block_lines:
                            block_text = "\n".join(config_block_lines)
                            block_entries = self._extract_from_config_block(block_text)
                            entries.extend(block_entries)

                    except Exception as e:
                        safe_e = SecurityValidator.sanitize_log_message(str(e))
                        logger.debug(
                            f"Error processing text_decode for {name}: {safe_e}"
                        )

                elif kind == "endpoint_list":
                    # Scrape IPs for the clean IP pool
                    # These are stored for use by ProxyWasher
                    valid_ips = []
                    for line in content.splitlines():
                        line = line.strip()
                        # Handle IP:port format
                        if ":" in line and not line.startswith("["):
                            ip = line.split(":")[0]
                        else:
                            ip = line.split("/")[0]  # Handle CIDR notation

                        # Validate IP format
                        if IP_REGEX.match(ip):
                            valid_ips.append(ip)

                    if valid_ips:
                        self.scraped_endpoints.extend(valid_ips[:max_entries])
                        logger.info(
                            f"Scraped {len(valid_ips[:max_entries])} clean endpoints from {name}"
                        )
                    # Note: endpoint_list doesn't produce Proxy entries directly

                # Fallback: Regex Scan
                # If specialized parsers yielded nothing, try brute-force regex on raw content
                if not entries and kind != "endpoint_list":
                    matches = WIREGUARD_REGEX.findall(content)
                    for priv_key, _address in matches:
                        # Address usually comes as "172.16.0.2/32" or just IP
                        # Note: _address is extracted but not used - make_entry uses auto endpoints
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

    def get_scraped_endpoints(self) -> List[str]:
        """
        Returns the list of scraped clean endpoint IPs.
        Can be used by ProxyWasher to supplement its clean_ips pool.
        """
        return self.scraped_endpoints.copy()
