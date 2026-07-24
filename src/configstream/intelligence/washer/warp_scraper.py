# SPDX-License-Identifier: AGPL-3.0-or-later
"""Scrape bounded WARP configuration sources with strict URL and line parsing."""

from __future__ import annotations

import base64
import binascii
import ipaddress
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from configstream.intelligence.washer.utils import make_entry
from configstream.models import Proxy
from configstream.security_validator import SecurityValidator

logger = logging.getLogger(__name__)

MAX_SOURCE_BYTES = 2 * 1024 * 1024
ALLOWED_SOURCE_HOSTS = frozenset({"raw.githubusercontent.com"})

WARP_SOURCES: List[Dict[str, Any]] = [
    {
        "name": "ircfspace/warpendpoint",
        "url": "https://raw.githubusercontent.com/ircfspace/warpendpoint/main/result/warp-ip.txt",
        "kind": "endpoint_list",
        "max_entries": 100,
    },
]


def _source_url_is_allowed(url: str) -> bool:
    parsed = urlparse(str(url))
    return (
        parsed.scheme == "https"
        and parsed.hostname in ALLOWED_SOURCE_HOSTS
        and not parsed.username
        and not parsed.password
        and parsed.port in (None, 443)
    )


def _parse_endpoint(value: str, default_port: int = 2408) -> Optional[Tuple[str, int]]:
    raw = str(value or "").strip()
    if not raw or len(raw) > 512:
        return None

    host = raw
    port = default_port
    if raw.startswith("["):
        end = raw.find("]")
        if end < 0:
            return None
        host = raw[1:end]
        suffix = raw[end + 1 :]
        if suffix:
            if not suffix.startswith(":"):
                return None
            try:
                port = int(suffix[1:])
            except ValueError:
                return None
    else:
        try:
            ipaddress.ip_address(raw.split("/", 1)[0])
            host = raw.split("/", 1)[0]
        except ValueError:
            if raw.count(":") == 1:
                host_part, port_part = raw.rsplit(":", 1)
                try:
                    port = int(port_part)
                except ValueError:
                    return None
                host = host_part
            elif "/" in raw:
                host = raw.split("/", 1)[0]

    try:
        normalized = str(ipaddress.ip_address(host))
    except ValueError:
        return None
    if not ipaddress.ip_address(normalized).is_global:
        return None
    if not 1 <= port <= 65535:
        return None
    return normalized, port


def _extract_private_key(line: str) -> Optional[str]:
    if "=" not in line:
        return None
    name, value = line.split("=", 1)
    if name.strip().lower() != "privatekey":
        return None
    key = value.strip()
    if len(key) != 44:
        return None
    try:
        decoded = base64.b64decode(key, validate=True)
    except (binascii.Error, ValueError):
        return None
    return key if len(decoded) == 32 else None


class WarpScraper:
    def __init__(self) -> None:
        self._timeout = 30.0
        self.scraped_endpoints: List[str] = []

    def _parse_warp_uri(self, uri: str) -> Proxy | None:
        try:
            if not uri.startswith("warp://") or len(uri) > 4096:
                return None
            parsed = urlparse("http://" + uri[len("warp://") :])
            private_key = unquote(parsed.username or "")
            host = parsed.hostname or "auto"
            port = parsed.port or 2408
            params = parse_qs(parsed.query, keep_blank_values=False)
            peer_pub = params.get("peer", [None])[0]
            reserved = [0, 0, 0]
            if "reserved" in params:
                values = params["reserved"][0].split(",")
                if len(values) > 3:
                    return None
                reserved = [int(value) for value in values]
            return make_entry("warp-uri", private_key, host, peer_pub, reserved, port)
        except (ValueError, TypeError) as exc:
            logger.debug("Rejected malformed WARP URI: %s", type(exc).__name__)
            return None

    def _extract_from_config_block(self, text: str) -> List[Proxy]:
        entries: List[Proxy] = []
        for raw_line in str(text).splitlines():
            if len(raw_line) > 4096:
                continue
            private_key = _extract_private_key(raw_line.strip())
            if private_key:
                entry = make_entry(
                    "config-block",
                    private_key,
                    "auto",
                    None,
                    [0, 0, 0],
                )
                if entry:
                    entries.append(entry)
        return entries

    async def _fetch_source(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        if not _source_url_is_allowed(url):
            logger.warning("Rejected non-allowlisted WARP source URL")
            return None
        response = await client.get(url, follow_redirects=False)
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > MAX_SOURCE_BYTES:
                    raise ValueError("WARP source exceeds size limit")
            except ValueError:
                raise ValueError("Invalid or oversized Content-Length") from None
        content = response.content
        if len(content) > MAX_SOURCE_BYTES:
            raise ValueError("WARP source exceeds size limit")
        return content.decode("utf-8", errors="replace")

    async def scrape_warp_sources(self) -> List[Proxy]:
        all_proxies: List[Proxy] = []
        endpoint_set: set[str] = set()

        async with httpx.AsyncClient(
            timeout=self._timeout,
            trust_env=False,
            headers={"Accept": "text/plain, application/json"},
        ) as client:
            for source in WARP_SOURCES:
                name = str(source.get("name", "unknown"))
                url = str(source.get("url", ""))
                kind = str(source.get("kind", ""))
                max_entries_raw = source.get("max_entries", 20)
                max_entries = (
                    max(0, min(int(max_entries_raw), 1000))
                    if isinstance(max_entries_raw, int)
                    else 20
                )
                try:
                    content = await self._fetch_source(client, url)
                    if not content:
                        continue
                    entries: List[Proxy] = []

                    if kind == "singbox":
                        data = json.loads(content)
                        outbounds = (
                            data.get("outbounds", []) if isinstance(data, dict) else []
                        )
                        for outbound in outbounds:
                            if (
                                not isinstance(outbound, dict)
                                or outbound.get("type") != "wireguard"
                            ):
                                continue
                            local_address = outbound.get("local_address", [])
                            if not isinstance(local_address, list):
                                local_address = [local_address]
                            entry = make_entry(
                                "scraped-sb",
                                str(outbound.get("private_key", "")),
                                "auto",
                                outbound.get("peer_public_key"),
                                list(outbound.get("reserved") or [0, 0, 0]),
                            )
                            if entry:
                                entries.append(entry)

                    elif kind == "text_decode":
                        decoded = content
                        compact = "".join(content.split())
                        if compact and len(compact) <= MAX_SOURCE_BYTES * 2:
                            try:
                                decoded_bytes = base64.b64decode(compact, validate=True)
                                if len(decoded_bytes) <= MAX_SOURCE_BYTES:
                                    decoded = decoded_bytes.decode(
                                        "utf-8", errors="replace"
                                    )
                            except (binascii.Error, ValueError) as exc:
                                logger.debug(
                                    "WARP source was not base64 text; parsing as plain text (%s)",
                                    type(exc).__name__,
                                )
                        for raw_line in decoded.splitlines():
                            line = raw_line.strip()
                            if line.startswith("warp://"):
                                entry = self._parse_warp_uri(line)
                                if entry:
                                    entries.append(entry)
                        entries.extend(self._extract_from_config_block(decoded))

                    elif kind == "endpoint_list":
                        for raw_line in content.splitlines():
                            line = raw_line.split("#", 1)[0].strip()
                            endpoint = _parse_endpoint(line)
                            if endpoint:
                                endpoint_set.add(endpoint[0])
                            if len(endpoint_set) >= max_entries:
                                break
                    else:
                        logger.warning("Ignoring unsupported WARP source kind %r", kind)
                        continue

                    if entries:
                        all_proxies.extend(entries[:max_entries])
                        logger.info(
                            "Scraped %d WARP candidates from %s",
                            min(len(entries), max_entries),
                            SecurityValidator.sanitize_log_message(name),
                        )
                except (
                    httpx.HTTPError,
                    json.JSONDecodeError,
                    ValueError,
                    TypeError,
                ) as exc:
                    logger.warning(
                        "Failed to process WARP source %s: %s",
                        SecurityValidator.sanitize_log_message(name),
                        type(exc).__name__,
                    )

        self.scraped_endpoints = sorted(endpoint_set)
        return all_proxies

    def get_scraped_endpoints(self) -> List[str]:
        return self.scraped_endpoints.copy()
