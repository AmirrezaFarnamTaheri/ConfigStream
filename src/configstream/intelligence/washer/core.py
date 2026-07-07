# SPDX-License-Identifier: AGPL-3.0-or-later
import shutil
import asyncio
import base64
import binascii
import json
import hashlib
import logging
import threading
import httpx
import time
from typing import List, Dict, Optional, Set, Any, Tuple
from cachetools import LRUCache  # type: ignore

from configstream.models import Proxy
from configstream.converters import to_singbox_outbound, update_chain_details
from configstream.warp_scanner import WarpScannerWorker
from configstream.intelligence.washer.warp_scraper import WarpScraper
from configstream.intelligence.washer.key_generator import (
    KeyGenerator,
)  # Import the new key generator
from configstream.tools.vwarp.manager import VwarpTool
from pathlib import Path
from configstream.intelligence.chaining import (
    find_optimal_relay,
    RelayCandidate,
    COUNTRIES,
)
from configstream.pipeline_stats import PipelineStats
from configstream.config import AppSettings
from configstream.constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS
from configstream.tagging import (
    get_flag_emoji,
    build_proxy_stack,
    format_proxy_name,
    ProxyTagger,
)
from .constants import (
    DEFAULT_WARP_SERVER_KEY,
    DEFAULT_CLEAN_IPS,
    FALLBACK_CLEAN_IPS,
    CLEAN_IP_SOURCES,
    OPTIMIZED_RESERVED,
)

logger = logging.getLogger(__name__)

# Cache settings to avoid repeated pydantic_settings instantiation in per-proxy hot paths
_SETTINGS_CACHE = AppSettings()


class ProxyWasher:
    def __init__(self, warp_keys_json: str):
        try:
            parsed = json.loads(warp_keys_json) if warp_keys_json else []
            if not isinstance(parsed, list):
                logger.warning(f"warp_keys_json is not a list, got {type(parsed)}")
                self._warp_keys: List[Dict[str, Any]] = []
            else:
                self._warp_keys = self._normalize_warp_keys(parsed)
                if self._warp_keys:
                    logger.info(f"Loaded {len(self._warp_keys)} WARP keys for washing")
                else:
                    # Don't log warning here, we will try to generate/fetch later
                    logger.debug("No initial WARP keys configured")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse warp_keys_json: {e}")
            self._warp_keys = []

        self.seen_chains: LRUCache[str, bool] = LRUCache(maxsize=50000)
        self._seen_chains_lock = threading.Lock()
        self._state_lock = threading.Lock()
        # asyncio.Lock must NOT be created in __init__ when the class is
        # instantiated from sync context (no running event loop).  Use a
        # lazy-init pattern so the lock is created on first async use.
        self._async_state_lock: Optional[asyncio.Lock] = None
        self._clean_ips: List[Tuple[str, int]] = []

        # Initialize defaults immediately if not provided
        if not self._warp_keys:
            env_keys = _SETTINGS_CACHE.WARP_KEY_POOL

            if env_keys and env_keys != "[]":
                try:
                    parsed = json.loads(env_keys)
                except json.JSONDecodeError:
                    # Fallback to comma-separated format
                    parsed = [k.strip() for k in env_keys.split(",") if k.strip()]

                if isinstance(parsed, list):
                    self._warp_keys = self._normalize_warp_keys(parsed)

        self.scanner = WarpScannerWorker()
        self.key_gen = KeyGenerator()

    @staticmethod
    def _normalize_wg_key(key: str) -> Optional[str]:
        if not key:
            return None
        cleaned = "".join(str(key).split())
        if not cleaned:
            return None
        cleaned = cleaned.replace("-", "+").replace("_", "/")
        pad = len(cleaned) % 4
        if pad:
            cleaned += "=" * (4 - pad)
        try:
            decoded = base64.b64decode(cleaned, validate=True)
        except (binascii.Error, ValueError):
            try:
                decoded = base64.b64decode(cleaned, validate=False)
            except Exception:
                return None
        if len(decoded) != 32:
            return None
        return cleaned

    @classmethod
    def _normalize_warp_keys(cls, entries: List[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        invalid_private = 0
        invalid_peer = 0
        for item in entries:
            if isinstance(item, dict):
                if "private_key" not in item:
                    if "private-key" in item:
                        item["private_key"] = item.pop("private-key")
                    elif "privateKey" in item:
                        item["private_key"] = item.pop("privateKey")
                private_key = cls._normalize_wg_key(item.get("private_key", ""))
                if private_key:
                    item["private_key"] = private_key
                    peer_key = item.get("peer_public_key")
                    if peer_key:
                        peer_norm = cls._normalize_wg_key(peer_key)
                        if peer_norm:
                            item["peer_public_key"] = peer_norm
                        else:
                            invalid_peer += 1
                            item.pop("peer_public_key", None)
                    normalized.append(item)
                else:
                    invalid_private += 1
                continue
            if isinstance(item, str):
                key_str = cls._normalize_wg_key(item)
                if key_str:
                    normalized.append({"private_key": key_str})
                else:
                    invalid_private += 1
        if invalid_private:
            logger.warning(
                "Dropped %d invalid WARP private keys during normalization.",
                invalid_private,
            )
        if invalid_peer and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Dropped %d invalid WARP peer public keys during normalization.",
                invalid_peer,
            )
        return normalized

    @property
    def warp_keys(self) -> List[Dict[str, Any]]:
        """Thread-safe read of warp_keys."""
        with self._state_lock:
            return self._warp_keys[:]

    @warp_keys.setter
    def warp_keys(self, value: List[Dict[str, Any]]) -> None:
        """Thread-safe write of warp_keys."""
        with self._state_lock:
            self._warp_keys = value

    @property
    def clean_ips(self) -> List[Tuple[str, int]]:
        """Thread-safe read of clean_ips."""
        with self._state_lock:
            return self._clean_ips[:]

    @clean_ips.setter
    def clean_ips(self, value: List[Tuple[str, int]]) -> None:
        """Thread-safe write of clean_ips."""
        with self._state_lock:
            self._clean_ips = value

    async def fetch_clean_ips(self) -> None:
        """
        Fetches the latest clean IPs for WARP endpoints.
        Uses async lock for the ENTIRE method to prevent N consumers
        from triggering N redundant fetches (check-then-act race).
        """
        if self._async_state_lock is None:
            self._async_state_lock = asyncio.Lock()
        async with self._async_state_lock:
            # Early exit: already populated by a previous caller
            if self._warp_keys and self._clean_ips:
                return

            current_keys = self._warp_keys[:]
            current_ips = self._clean_ips[:]

            # --- STRATEGY 0.5: WARP KEYS & IPs FROM SCRAPER (Priority 1) ---
            if not current_keys or not current_ips:
                try:
                    scraper = WarpScraper()
                    scraped_keys = await scraper.scrape_warp_sources()

                    fresh_endpoints = scraper.get_scraped_endpoints()
                    new_keys = []

                    for p in scraped_keys:
                        key_dict = {
                            "private_key": p.details.get("private_key"),
                            "peer_public_key": p.details.get("peer_public_key"),
                            "id": p.uuid,
                        }
                        if key_dict["private_key"] and key_dict["peer_public_key"]:
                            new_keys.append(key_dict)

                    if fresh_endpoints:
                        self._clean_ips = []
                        for ep in fresh_endpoints:
                            if isinstance(ep, str):
                                if self._looks_like_ip(ep):
                                    self._clean_ips.append((ep, 2408))
                            elif isinstance(ep, tuple) and len(ep) == 2:
                                if self._looks_like_ip(str(ep[0])):
                                    self._clean_ips.append(ep)
                        if self._clean_ips:
                            logger.info(
                                f"Loaded {len(self._clean_ips)} clean IPs from Scraper"
                            )

                    if new_keys:
                        self._warp_keys = new_keys
                        logger.info(
                            f"Loaded {len(new_keys)} WARP keys from community sources"
                        )
                except Exception as e:
                    logger.warning(f"WARP scraper failed: {e}")

            # --- STRATEGY 0: VWARP SCANNER (Priority 2 if Scraper insufficient) ---
            if not self._clean_ips:
                try:
                    vwarp = VwarpTool()
                    if await vwarp.is_available():
                        scanned_ips_vwarp = await vwarp.scan_endpoints()
                        if scanned_ips_vwarp:
                            self._clean_ips = list(scanned_ips_vwarp)
                            logger.info(
                                f"Loaded {len(scanned_ips_vwarp)} clean IPs from Vwarp"
                            )
                    else:
                        logger.debug("Vwarp binary not found - skipping Vwarp scan.")
                except Exception as e:
                    logger.warning(f"Vwarp scanner failed: {e}")

            # --- STRATEGY 1: ACTIVE SCANNING ---
            if self.scanner.available and not self._clean_ips:
                try:
                    logger.info("Attempting active IP scan...")
                    scanned_ips = await self.scanner.scan_endpoints(
                        limit=50, timeout=5, max_latency=800
                    )

                    if scanned_ips and len(scanned_ips) >= 5:
                        self._clean_ips = [
                            (ip, 2408)
                            for ip in scanned_ips
                            if self._looks_like_ip(str(ip))
                        ]
                        logger.info(
                            f"Active Scan Success: Using {len(self._clean_ips)} fresh IPs."
                        )
                except Exception as e:
                    logger.error(f"Active scan failed: {e}")

            # --- STRATEGY 2: STATIC LISTS ---
            if not self._clean_ips:
                logger.info("Starting static list fetch sequence...")
                for source_url in CLEAN_IP_SOURCES:
                    try:
                        async with httpx.AsyncClient(
                            timeout=10, trust_env=False
                        ) as client:
                            resp = await client.get(source_url)
                            if resp.status_code == 200:
                                lines = [
                                    line.strip()
                                    for line in resp.text.splitlines()
                                    if line.strip() and not line.startswith("#")
                                ]
                                valid_ips: list[str] = []
                                for raw_ip in lines:
                                    host = raw_ip.split("/")[0]
                                    if host.count(".") != 3 or not host[0].isdigit():
                                        continue
                                    # CIDR base addresses (x.x.x.0) are not usable
                                    # endpoints; offset to a real host IP.
                                    octets = host.split(".")
                                    try:
                                        last = int(octets[3])
                                    except (IndexError, ValueError):
                                        continue
                                    if last == 0:
                                        octets[3] = "1"
                                        host = ".".join(octets)
                                    elif last == 255:
                                        octets[3] = "254"
                                        host = ".".join(octets)
                                    if self._looks_like_ip(host):
                                        valid_ips.append(host)
                                if valid_ips:
                                    self._clean_ips = [
                                        (ip, 2408) for ip in valid_ips[:100]
                                    ]
                                    logger.info(
                                        f"Fetched {len(valid_ips)} clean IPs from {source_url.split('/')[2]}"
                                    )
                                    break  # Stop after one success
                    except Exception:  # nosec B110
                        pass

            # --- STRATEGY 3: DEFAULTS ---
            if not self._clean_ips:
                logger.warning(
                    f"All scanners failed. Using {len(DEFAULT_CLEAN_IPS)} default IPs."
                )
                self._clean_ips = [(ip, 2408) for ip in DEFAULT_CLEAN_IPS]

            # --- KEY GENERATION FALLBACK (Last Resort) ---
            # If still no keys, try to generate one
            if not self._warp_keys:
                logger.info(
                    "No WARP keys found. Attempting to generate a new account..."
                )
                try:
                    new_account = await self.key_gen.generate_account()
                    if new_account:
                        self._warp_keys = [new_account]
                        logger.info("Successfully generated a new WARP account/key.")
                    else:
                        logger.error(
                            "Failed to generate WARP account. Washing disabled."
                        )
                except Exception as e:
                    logger.error(f"Key generation failed: {e}")

    @staticmethod
    def _looks_like_ip(host: str) -> bool:
        """Quick check that a host string resembles an IP (not a timestamp/garbage)."""
        host = host.strip()
        if not host:
            return False
        # IPv4: starts with digit and has exactly 3 dots
        if host[0].isdigit() and host.count(".") == 3:
            return all(
                part.isdigit() and 0 <= int(part) <= 255 for part in host.split(".")
            )
        # IPv6: hex/colon/dot chars only AND at least 2 colons (real IPv6 has 2-7)
        if host.count(":") >= 2 and all(c in "0123456789abcdefABCDEF:." for c in host):
            return True
        return False

    def _get_clean_endpoint(self, relay_id: str) -> Tuple[str, int]:
        pool = self.clean_ips
        if not pool:
            # Parse fallback IPs
            pool = []
            for item in FALLBACK_CLEAN_IPS:
                host = str(item).strip()
                if not host:
                    continue

                ip = host
                port = 2408

                if host.startswith("[") and "]" in host:
                    # Bracketed IPv6: [addr]:port — strip brackets
                    end = host.find("]")
                    ip = host[1:end]
                    rest = host[end + 1 :].lstrip()
                    if rest.startswith(":"):
                        try:
                            port = int(rest[1:])
                        except ValueError:
                            continue
                elif ":" in host:
                    ip_part, port_part = host.rsplit(":", 1)
                    try:
                        port = int(port_part)
                    except ValueError:
                        continue
                    ip = ip_part

                if not (1 <= port <= 65535):
                    continue

                pool.append((ip, port))
            # Append defaults
            pool.extend([(ip, 2408) for ip in DEFAULT_CLEAN_IPS])

        # Filter out any non-IP entries that slipped through scan parsing
        valid_pool = []
        for ep in pool:
            if isinstance(ep, tuple) and len(ep) == 2:
                if self._looks_like_ip(str(ep[0])):
                    valid_pool.append(ep)
            elif isinstance(ep, str) and self._looks_like_ip(ep):
                valid_pool.append((ep, 2408))

        if not valid_pool:
            return ("162.159.192.1", 2408)

        hash_val = int(hashlib.sha256(relay_id.encode()).hexdigest(), 16)
        return valid_pool[hash_val % len(valid_pool)]

    def _get_consistent_exit(
        self, relay_id: str, exit_pool: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not exit_pool:
            return None

        current_epoch = int(time.time() / (7 * 86400))
        hash_input = f"{relay_id}-{current_epoch}".encode()
        hash_val = int(hashlib.sha256(hash_input).hexdigest(), 16)

        pool_len = len(exit_pool)
        start_index = hash_val % pool_len

        for i in range(pool_len):
            idx = (start_index + i) % pool_len
            key = exit_pool[idx]
            # Allow key if it has private key, inject peer key if missing
            if key.get("private_key"):
                return key

        return None

    def _get_optimized_reserved(self, seed: str) -> List[int]:
        """
        Selects a reserved bytes array from OPTIMIZED_RESERVED deterministically based on seed.
        """
        if not OPTIMIZED_RESERVED:
            return [0, 0, 0]  # Default fallback

        h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        return OPTIMIZED_RESERVED[h % len(OPTIMIZED_RESERVED)]

    def _generate_deterministic_ip(self, seed: str) -> str:
        h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        # Use 10.x.x.x range for 16M+ unique IPs
        # Bit shift to utilize more of the hash entropy
        octet_2 = (h >> 16) % 255
        octet_3 = (h >> 8) % 255
        octet_4 = (h % 254) + 1  # 1-254
        return f"10.{octet_2}.{octet_3}.{octet_4}/32"

    def get_warp_config(self, seed: str) -> Optional[Dict[str, Any]]:
        """
        Generate a WARP WireGuard config for a given seed (used by chaining.py).
        Returns None if no WARP keys are available.
        """
        exit_key = self._get_consistent_exit(seed, self.warp_keys)
        if not exit_key:
            return None

        endpoint_data = self._get_clean_endpoint(seed)
        if isinstance(endpoint_data, tuple):
            clean_endpoint, clean_port = endpoint_data
        else:
            clean_endpoint = str(endpoint_data)
            clean_port = 2408

        unique_ip = self._generate_deterministic_ip(seed)

        reserved = self._get_optimized_reserved(seed)

        # Ensure valid peer public key
        # Check environment or use default
        peer_key = exit_key.get("peer_public_key")
        if not peer_key:
            peer_key = _SETTINGS_CACHE.WARP_PEER_KEY or DEFAULT_WARP_SERVER_KEY

        return {
            "type": "wireguard",
            "local_address": [unique_ip],
            "private_key": exit_key["private_key"],
            "server": clean_endpoint,
            "server_port": clean_port,
            "peer_public_key": peer_key,
            "reserved": reserved,
            "mtu": 1280,
        }

    def _has_vwarp_binary(self) -> bool:
        """Best-effort local binary presence check."""
        if shutil.which("vwarp"):
            return True
        return Path("vwarp").exists() or Path("/usr/local/bin/vwarp").exists()

    def is_vwarp_available(self) -> bool:
        """
        Synchronous compatibility check.

        NOTE:
        This method intentionally avoids blocking socket probes. Async code paths
        should use ``is_vwarp_available_async`` for live tunnel checks.
        """
        return self._has_vwarp_binary()

    async def is_vwarp_available_async(self) -> bool:
        """Check binary presence and local SOCKS reachability without blocking."""
        if not self._has_vwarp_binary():
            return False
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(VWARP_BIND_ADDRESS, VWARP_SOCKS5_PORT),
                timeout=0.25,
            )
            writer.close()
            await writer.wait_closed()
            _ = reader  # keep reference for type checkers
            return True
        except Exception:
            return False

    def wash_failed(
        self,
        failed_proxies: List[Proxy],
        stats: Optional[PipelineStats] = None,
        use_vwarp: bool = False,
    ) -> Tuple[List[Proxy], int]:
        """
        Attempts to REVIVE failed proxies by wrapping them in WARP.
        Returns a list of NEW Proxy objects (the chains) ready for re-testing.
        """
        revived_candidates: List[Proxy] = []
        revived_count = 0

        if not self.warp_keys:
            return [], 0

        # Prevent infinite recursion: Filter out proxies that are already revived
        candidates = [
            p
            for p in failed_proxies
            if p.protocol != "revived" and not p.details.get("is_revived")
        ]

        for relay in candidates:
            # Basic plausibility check before reviving
            if not relay.address or not relay.port:
                continue

            exit_key = self._get_consistent_exit(relay.id, self.warp_keys)
            if not exit_key:
                continue

            # Use different tag prefixes for WARP vs Vwarp revivals
            if use_vwarp:
                chain_id = f"VWARP-REVIVE-{relay.id[:8]}"
                relay_tag_prefix = "VWARP-RELAY"
            else:
                chain_id = f"WARP-REVIVE-{relay.id[:8]}"
                relay_tag_prefix = "WARP-RELAY"
            process_tag = "revived-vwarp" if use_vwarp else "revived-warp"

            endpoint_data = self._get_clean_endpoint(relay.id)
            if isinstance(endpoint_data, tuple):
                clean_endpoint, clean_port = endpoint_data
            else:
                clean_endpoint = str(endpoint_data)
                clean_port = 2408

            unique_ip = self._generate_deterministic_ip(chain_id)

            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                continue

            relay_out["tag"] = f"{relay_tag_prefix}-{relay.id[:8]}"
            relay_out["_origin_country_code"] = relay.country_code or ""
            relay_out["_origin_latency"] = relay.latency

            reserved_bytes = self._get_optimized_reserved(chain_id)

            # Ensure valid peer public key
            peer_key = exit_key.get("peer_public_key")
            if not peer_key:
                peer_key = _SETTINGS_CACHE.WARP_PEER_KEY or DEFAULT_WARP_SERVER_KEY

            if use_vwarp:
                # Vwarp Revival: Client -> Vwarp (SOCKS5) -> Relay
                # Use local Vwarp tunnel to unblock access to the Relay
                warp_out = {
                    "type": "socks",
                    "tag": chain_id,
                    "server": VWARP_BIND_ADDRESS,
                    "server_port": VWARP_SOCKS5_PORT,
                    "version": "5",
                }
                # Detour Relay through Vwarp
                relay_out["detour"] = chain_id
            else:
                # Standard Revival: Client -> Relay -> Warp
                # Use Relay to tunnel Warp (Warp over Proxy)
                warp_out = {
                    "type": "wireguard",
                    "tag": chain_id,
                    "local_address": [unique_ip],
                    "private_key": exit_key["private_key"],
                    "server": clean_endpoint,
                    "server_port": clean_port,
                    "peer_public_key": peer_key,
                    "reserved": reserved_bytes,
                    "mtu": 1280,
                    "detour": relay_out["tag"],
                }

            # We bundle BOTH outbounds into the proxy details for special handling
            # Serialize relay object to prevent JSON errors.
            # Use the canonical Pydantic method for serialization.
            origin_dict = relay.model_dump(mode="json")

            # Canonical protocol-agnostic chain representation.
            relay_chain = relay.model_copy(deep=True)
            relay_chain.details = dict(relay_chain.details or {})
            relay_chain.details["tag"] = relay_out["tag"]
            if use_vwarp:
                relay_chain.details["detour"] = chain_id

            if use_vwarp:
                warp_chain = Proxy(
                    config=f"socks5://{VWARP_BIND_ADDRESS}:{VWARP_SOCKS5_PORT}",
                    protocol="socks5",
                    address=VWARP_BIND_ADDRESS,
                    port=VWARP_SOCKS5_PORT,
                    details={
                        "tag": chain_id,
                        "version": "5",
                    },
                    is_working=True,
                    process=process_tag,
                )
            else:
                warp_chain = Proxy(
                    config=f"wireguard://{exit_key['private_key']}@{clean_endpoint}:{clean_port}",
                    protocol="wireguard",
                    address=clean_endpoint,
                    port=clean_port,
                    details={
                        "tag": chain_id,
                        "private_key": exit_key["private_key"],
                        "peer_public_key": peer_key,
                        "local_address": [unique_ip],
                        "reserved": reserved_bytes,
                        "mtu": 1280,
                        "detour": relay_out["tag"],
                    },
                    is_working=True,
                    process=process_tag,
                )

            vwarp_mode = "STANDARD"
            if use_vwarp:
                settings = AppSettings()
                if settings.VWARP_MASQUE_ENABLED:
                    vwarp_mode = "MASQUE"

            # Sing-box requires detour targets before referrers. Vwarp: relay detours to warp
            # → warp first. Standard WARP: warp detours to relay → relay first.
            chain_order = [warp_out, relay_out] if use_vwarp else [relay_out, warp_out]
            chain_proxies = (
                [warp_chain, relay_chain] if use_vwarp else [relay_chain, warp_chain]
            )
            revived_details: Dict[str, Any] = {
                # Canonical chain data model (protocol-agnostic Proxy objects).
                "chain": chain_proxies,
                "is_revived": True,
                "use_vwarp": use_vwarp,
                "vwarp_mode": vwarp_mode if use_vwarp else None,
                "origin_proxy": origin_dict,
                "origin_id": relay.id,
            }
            # Keep legacy chain in sync for downstream compatibility.
            update_chain_details(revived_details, chain_order)

            revived_proxy = Proxy(
                config=f"revived://{relay.address}",  # Dummy config
                protocol="revived",  # Special protocol
                address=clean_endpoint,
                port=clean_port,
                # Top-level `uuid` in public artifact schema is UUID-typed.
                # Keep chain identifiers inside revived details/tags.
                uuid="",
                remarks="",  # Set below via format_proxy_name
                process=process_tag,
                details=revived_details,
            )
            # Unified scheme: geo | tech/protocol stack | latency | process | etc
            _tpl = _SETTINGS_CACHE.RENAME_TEMPLATE or ProxyTagger.DEFAULT_TEMPLATE
            revived_proxy.remarks = format_proxy_name(_tpl, revived_proxy)

            revived_candidates.append(revived_proxy)
            revived_count += 1

            if stats:
                lock = getattr(stats, "_lock", None)
                if lock:
                    with lock:
                        if use_vwarp:
                            stats.vwarp_attempts += 1
                        else:
                            stats.warp_attempts += 1
                else:
                    if use_vwarp:
                        stats.vwarp_attempts += 1
                    else:
                        stats.warp_attempts += 1

        return revived_candidates, revived_count

    def wash_batch(
        self, proxies: List[Proxy], stats: Optional[PipelineStats] = None
    ) -> Tuple[List[Dict[str, Any]], Set[str], Dict[str, int]]:
        """
        Standard Washing: Process WORKING proxies to create WARP chains.
        """
        washed_outbounds: List[Dict[str, Any]] = []
        washed_ids: Set[str] = set()
        skip_reasons: Dict[str, int] = {}

        keys = self.warp_keys
        if not keys:
            return washed_outbounds, washed_ids, skip_reasons

        candidates = [p for p in proxies if p.is_working]

        target_exit = RelayCandidate("US", 37.09, -95.71, "wireguard")
        origin_country = _SETTINGS_CACHE.OPTIMAL_RELAY_ORIGIN

        for relay in candidates:
            exit_key = self._get_consistent_exit(relay.id, keys)
            if not exit_key:
                skip_reasons["invalid_warp_key"] = (
                    skip_reasons.get("invalid_warp_key", 0) + 1
                )
                continue

            chain_id = f"CHAIN-{relay.country_code}-{relay.id[:6]}-{exit_key.get('id', '00')[:4]}"

            with self._seen_chains_lock:
                if chain_id in self.seen_chains:
                    skip_reasons["duplicate_chain"] = (
                        skip_reasons.get("duplicate_chain", 0) + 1
                    )
                    continue
                self.seen_chains[chain_id] = True

            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                continue

            relay_tag = f"RELAY-{chain_id}"
            relay_out["tag"] = relay_tag
            relay_out["_origin_country_code"] = relay.country_code or ""
            relay_out["_origin_latency"] = relay.latency

            endpoint_data = self._get_clean_endpoint(relay.id)
            if isinstance(endpoint_data, tuple):
                clean_endpoint, clean_port = endpoint_data
            else:
                clean_endpoint = str(endpoint_data)
                clean_port = 2408

            unique_ip = self._generate_deterministic_ip(chain_id)

            is_optimal = False
            try:
                if relay.country_code and relay.country_code in COUNTRIES:
                    # Pass measured latency for better optimization
                    relay_candidate = RelayCandidate(
                        relay.country_code,
                        0.0,
                        0.0,
                        relay.protocol,
                        latency=relay.latency or 0.0,
                    )
                    relay_candidate.lat, relay_candidate.lon = COUNTRIES[
                        relay.country_code
                    ]
                    res = find_optimal_relay(
                        origin_country, target_exit, [relay_candidate]
                    )
                    if isinstance(res, dict) and "relay" in res:
                        if float(res.get("total_distance", 99999)) < 15000:
                            is_optimal = True
            except Exception:  # nosec B110
                pass

            flag = get_flag_emoji(relay.country_code or "XX")
            lat_str = f"{int(relay.latency)}ms" if relay.latency else "N/A"
            stack = build_proxy_stack(relay)
            tier = "🛡️ OPTIMAL" if is_optimal else "🛡️ SECURE"

            # Unified scheme: geo | tech/protocol stack | latency | etc (like naive proxies)
            exit_tag = f"{flag} | {stack} | {tier} | WARP | {lat_str}"

            reserved_bytes = self._get_optimized_reserved(chain_id)

            # Ensure valid peer public key
            peer_key = exit_key.get("peer_public_key")
            if not peer_key:
                peer_key = _SETTINGS_CACHE.WARP_PEER_KEY or DEFAULT_WARP_SERVER_KEY

            warp_out = {
                "type": "wireguard",
                "tag": exit_tag,
                "local_address": [unique_ip],
                "private_key": exit_key["private_key"],
                "server": clean_endpoint,
                "server_port": clean_port,
                "peer_public_key": peer_key,
                "reserved": reserved_bytes,
                "mtu": 1280,
                "detour": relay_tag,
            }

            washed_outbounds.append(relay_out)
            # Add metadata for process tracking
            warp_out["_process"] = "washed"
            washed_outbounds.append(warp_out)
            washed_ids.add(relay.id)
            if stats:
                lock = getattr(stats, "_lock", None)
                if lock:
                    with lock:
                        stats.warp_attempts += 1
                else:
                    stats.warp_attempts += 1

        if stats:
            lock = getattr(stats, "_lock", None)
            if lock:
                with lock:
                    stats.washer_success_count = len(washed_ids)
            else:
                stats.washer_success_count = len(washed_ids)

        return washed_outbounds, washed_ids, skip_reasons

    def create_revived_proxy(
        self,
        entry_outbound: Dict[str, Any],
        exit_outbound: Dict[str, Any],
        process: str = "washed",
    ) -> Proxy:
        """
        Builds a 'revived' Proxy model from two outbounds forming a chain.
        This model can be passed to SingBoxTester for active verification.
        """
        # The 'exit' outbound typically carries the user-visible tag and geo info
        # if it was derived from a native proxy.
        details = {
            "chain": [entry_outbound, exit_outbound],
            "is_revived": True,
            "process": process,
        }

        # Determine country and city from outbounds if possible
        country = exit_outbound.get("_origin_country_code") or ""
        latency = exit_outbound.get("_origin_latency") or 0.0

        return Proxy(
            config="chain://",
            protocol="revived",
            address=exit_outbound.get("server", "127.0.0.1"),
            port=exit_outbound.get("server_port", 0),
            remarks=exit_outbound.get("tag", "Revived Chain"),
            country_code=country,
            latency=latency,
            process=process,
            details=details,
            is_working=False,  # Starts as False until verified
        )

    def shield_batch(
        self,
        proxies: List[Proxy],
        stats: Optional[PipelineStats] = None,
    ) -> Tuple[List[Dict[str, Any]], Set[str]]:
        """
        [ALCHEMY MODE] Shields dead proxies behind a WARP tunnel.
        Topology: Client -> WARP (Clean Endpoint) -> Proxy -> Internet

        This converts 'Dead Copper' (Blocked Proxy) into 'Gold' (Tunnelled Proxy).
        Use this to UNBLOCK dead proxies by inverting the topology.
        """
        shielded_outbounds: List[Dict[str, Any]] = []
        shielded_ids: Set[str] = set()

        if not self.warp_keys:
            return [], set()

        # Iterate through proxies (typically those that failed direct connection)
        for i, relay in enumerate(proxies):
            # 1. Generate the Shield (WARP Config)
            # This uses your existing logic to get clean IPs and keys
            warp_out = self.get_warp_config(relay.id)
            if not warp_out:
                continue

            # Tag the shield uniquely
            shield_tag = f"SHIELD-{relay.country_code or 'XX'}-{i}"
            warp_out["tag"] = shield_tag
            warp_out["_process"] = "shield_base"

            # CRITICAL: The Shield connects DIRECTLY to the internet (or via local gateway)
            # It does NOT use a detour. It IS the transport.
            warp_out.pop("detour", None)  # Remove any existing detour

            # 2. Convert the 'Dirty' Proxy
            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                continue

            relay_out["_origin_country_code"] = relay.country_code or ""
            relay_out["_origin_latency"] = relay.latency

            # 3. THE ALCHEMY: Wrap the Proxy INSIDE the Shield
            # Sing-box logic: "detour" means "send this outbound's traffic through..."
            relay_out["detour"] = shield_tag

            # 4. Branding & Optimization
            # Unified scheme: geo | tech/protocol stack | latency | process | etc
            # CRITICAL: Append relay.id[:8] so each chain has a UNIQUE tag. Without this,
            # format_proxy_name can produce identical tags for similar proxies, causing
            # _append_chain to skip chains and collapse thousands into one "single proxy".
            shield_proxy = Proxy(
                config=relay.config or "",
                protocol=relay.protocol or "unknown",
                address=relay.address,
                port=relay.port,
                uuid=relay.uuid or "",
                remarks=relay.remarks or "",
                country_code=relay.country_code or "",
                city=relay.city or "",
                latency=relay.latency,
                is_working=relay.is_working,
                process="shielded",
                details=(relay.details or {}) | {"is_shielded": True},
            )
            _tpl = _SETTINGS_CACHE.RENAME_TEMPLATE or ProxyTagger.DEFAULT_TEMPLATE
            base_tag = format_proxy_name(_tpl, shield_proxy)
            relay_out["tag"] = f"{base_tag} | {relay.id[:8]}"
            relay_out["_process"] = "shield_payload"
            # Keep shield metadata on outbound only.
            # Do not mutate the source proxy object (process/details), otherwise
            # native/revived labels are lost in final outputs and merge stage.
            relay_out["_is_shielded"] = True

            # 5. Append to output
            # Order: Shield first, then Proxy (though Sing-box resolves by tag)
            shielded_outbounds.append(warp_out)
            shielded_outbounds.append(relay_out)
            shielded_ids.add(relay.id)

            # 6. Update Stats
            if stats:
                lock = getattr(stats, "_lock", None)
                if lock:
                    with lock:
                        stats.warp_attempts += 1
                else:
                    stats.warp_attempts += 1

        return shielded_outbounds, shielded_ids
