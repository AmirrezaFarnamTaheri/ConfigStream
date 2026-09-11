# SPDX-License-Identifier: AGPL-3.0-or-later
"""IP blocklist manager with conditional downloads and indexed lookups."""

import asyncio
import ipaddress
import json
import logging
import threading
from pathlib import Path
from typing import Optional, Set

import aiofiles  # type: ignore[import-untyped]
import httpx

from configstream.utils import AtomicFileWriter

logger = logging.getLogger(__name__)

BLOCKLIST_URL = "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"
CACHE_FILE = Path("data/firehol_level1.netset")
METADATA_FILE = Path("data/firehol_level1.metadata.json")
HONEYPOT_PORTS = {23, 2323}
HONEYPOT_ASNS: Set[str] = set()
MIN_BLOCKLIST_NETWORKS = 100
MAX_INVALID_LINE_RATIO = 0.05
MIN_LKG_RETAINED_RATIO = 0.50


class BlocklistManager:
    _instance: Optional["BlocklistManager"] = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self.blocked_networks: Set[ipaddress.IPv4Network | ipaddress.IPv6Network] = (
            set()
        )
        self._v4_index: dict[int, Set[ipaddress.IPv4Network]] = {}
        self._v6_index: dict[int, Set[ipaddress.IPv6Network]] = {}
        self._v4_broad: Set[ipaddress.IPv4Network] = set()
        self._v6_broad: Set[ipaddress.IPv6Network] = set()
        self._data_lock: Optional[asyncio.Lock] = None
        self._initialized = True

    def _get_lock(self) -> asyncio.Lock:
        if self._data_lock is None:
            self._data_lock = asyncio.Lock()
        return self._data_lock

    @staticmethod
    def _read_metadata() -> dict[str, str]:
        try:
            data = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    key: str(value)
                    for key, value in data.items()
                    if key in {"etag", "last_modified"} and value
                }
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.debug("Ignoring unusable blocklist metadata: %s", type(exc).__name__)
        return {}

    @staticmethod
    def _write_metadata(response: httpx.Response) -> None:
        def header(name: str) -> str:
            value = response.headers.get(name, "")
            return value if isinstance(value, str) else ""

        metadata = {
            "etag": header("ETag"),
            "last_modified": header("Last-Modified"),
        }
        AtomicFileWriter.write_text(METADATA_FILE, json.dumps(metadata, sort_keys=True))

    @staticmethod
    def _parse_candidate(
        content: bytes, *, enforce_sanity: bool
    ) -> Set[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Parse a candidate without mutating the last-known-good cache."""

        if not content or len(content) > 50 * 1024 * 1024:
            raise ValueError("Blocklist response has an invalid size")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Blocklist response is not valid UTF-8") from exc

        networks: Set[ipaddress.IPv4Network | ipaddress.IPv6Network] = set()
        invalid = 0
        candidate_lines = 0
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            candidate_lines += 1
            try:
                networks.add(ipaddress.ip_network(line, strict=False))
            except ValueError:
                invalid += 1

        if enforce_sanity:
            if len(networks) < MIN_BLOCKLIST_NETWORKS:
                raise ValueError(
                    f"Blocklist candidate contains only {len(networks)} valid networks"
                )
            if candidate_lines and invalid / candidate_lines > MAX_INVALID_LINE_RATIO:
                raise ValueError(
                    "Blocklist candidate contains too many invalid entries"
                )
        return networks

    @classmethod
    def _validate_candidate_against_cache(
        cls, content: bytes
    ) -> Set[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        networks = cls._parse_candidate(content, enforce_sanity=True)
        if CACHE_FILE.is_file():
            try:
                cached = cls._parse_candidate(
                    CACHE_FILE.read_bytes(), enforce_sanity=False
                )
            except (OSError, ValueError):
                cached = set()
            if len(cached) >= MIN_BLOCKLIST_NETWORKS:
                minimum = max(
                    MIN_BLOCKLIST_NETWORKS,
                    int(len(cached) * MIN_LKG_RETAINED_RATIO),
                )
                if len(networks) < minimum:
                    raise ValueError(
                        "Blocklist candidate shrank below the last-known-good safety floor"
                    )
        return networks

    async def update(self) -> None:
        """Refresh the blocklist, reusing the cache on HTTP 304 or errors."""
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        metadata = await asyncio.to_thread(self._read_metadata)
        headers: dict[str, str] = {}
        if metadata.get("etag"):
            headers["If-None-Match"] = metadata["etag"]
        if metadata.get("last_modified"):
            headers["If-Modified-Since"] = metadata["last_modified"]

        try:
            async with httpx.AsyncClient(
                trust_env=False, follow_redirects=False
            ) as client:
                response = await client.get(BLOCKLIST_URL, timeout=30, headers=headers)

            if response.status_code == 304:
                logger.info("FireHol blocklist is unchanged; using cached copy")
                await self.load()
                return

            response.raise_for_status()
            content = response.content
            await asyncio.to_thread(self._validate_candidate_against_cache, content)

            temp_file = CACHE_FILE.with_suffix(CACHE_FILE.suffix + ".tmp")
            try:
                async with aiofiles.open(temp_file, "wb") as handle:
                    await handle.write(content)
                await asyncio.to_thread(temp_file.replace, CACHE_FILE)
            finally:
                temp_file.unlink(missing_ok=True)
            await asyncio.to_thread(self._write_metadata, response)
            logger.info("Updated verified FireHol blocklist successfully")
        except (httpx.HTTPError, OSError, ValueError) as exc:
            logger.warning(
                "Blocklist update failed (%s); using cached version if available",
                type(exc).__name__,
            )
        await self.load()

    async def load(self) -> None:
        if not CACHE_FILE.exists():
            return

        try:
            content = await asyncio.to_thread(CACHE_FILE.read_bytes)
            new_networks = await asyncio.to_thread(
                self._parse_candidate, content, enforce_sanity=False
            )
        except (OSError, ValueError) as exc:
            logger.error("Unable to load blocklist cache: %s", type(exc).__name__)
            return

        v4_index: dict[int, Set[ipaddress.IPv4Network]] = {}
        v6_index: dict[int, Set[ipaddress.IPv6Network]] = {}
        v4_broad: Set[ipaddress.IPv4Network] = set()
        v6_broad: Set[ipaddress.IPv6Network] = set()
        for network in new_networks:
            if isinstance(network, ipaddress.IPv4Network):
                if network.prefixlen < 8:
                    v4_broad.add(network)
                else:
                    v4_index.setdefault(
                        int(network.network_address.packed[0]), set()
                    ).add(network)
            else:
                if network.prefixlen < 16:
                    v6_broad.add(network)
                else:
                    first_segment = (int(network.network_address.packed[0]) << 8) | int(
                        network.network_address.packed[1]
                    )
                    v6_index.setdefault(first_segment, set()).add(network)

        async with self._get_lock():
            self.blocked_networks = new_networks
            self._v4_index = v4_index
            self._v6_index = v6_index
            self._v4_broad = v4_broad
            self._v6_broad = v6_broad
        logger.info(
            "Loaded %d blocked networks from FireHol Level 1", len(new_networks)
        )

    def is_blocked(self, address: str) -> bool:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False

        if isinstance(ip, ipaddress.IPv4Address):
            bucket = self._v4_index.get(int(ip.packed[0]), ())
            return any(ip in network for network in self._v4_broad) or any(
                ip in network for network in bucket
            )

        first_segment = (int(ip.packed[0]) << 8) | int(ip.packed[1])
        bucket_v6 = self._v6_index.get(first_segment, ())
        return any(ip in network for network in self._v6_broad) or any(
            ip in network for network in bucket_v6
        )

    def is_suspicious_port(self, port: int) -> bool:
        return int(port) in HONEYPOT_PORTS


DEFAULT_BLOCKLIST = BlocklistManager()
