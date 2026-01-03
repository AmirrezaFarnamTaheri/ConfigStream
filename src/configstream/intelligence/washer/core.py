# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
import hashlib
import logging
import threading
import os
import httpx
import time
from typing import List, Dict, Optional, Set, Any, Tuple
from cachetools import LRUCache

from configstream.models import Proxy
from configstream.converters import to_singbox_outbound
from configstream.workers.scanner import WarpScannerWorker
from configstream.intelligence.washer.warp_scraper import WarpScraper
from configstream.intelligence.washer.key_generator import (
    KeyGenerator,
)  # [FIX] Import the new key generator
from configstream.tools.vwarp import VwarpTool
from configstream.intelligence.chaining import find_optimal_relay, ProxyStub, COUNTRIES
from configstream.pipeline_core.stats import PipelineStats
from configstream.config import AppSettings

logger = logging.getLogger(__name__)

# Static fallback if fetch fails
DEFAULT_CLEAN_IPS = ["162.159.192.1", "162.159.193.10", "162.159.195.5"]

# Fallback Clean IPs from user reports
FALLBACK_CLEAN_IPS = [
    "188.114.97.204:7103",
    "188.114.99.73:2506",
    "162.159.192.166:5956",
    "188.114.99.120:1074",
    "162.159.192.253:7103",
    "188.114.99.153:5956",
    "188.114.99.73:955",
    "188.114.96.101:2506",
    "188.114.97.204:1002",
    "188.114.98.201:7103",
    "162.159.192.253:890",
    "162.159.192.83:890",
    "188.114.98.224:3476",
    "188.114.98.224:500",
    "188.114.98.224:2371",
    "188.114.98.224:1070",
    "188.114.98.224:854",
    "188.114.98.224:864",
    "188.114.98.224:939",
    "188.114.98.224:2408",
    "188.114.98.224:908",
    "188.114.96.145:1074",
    "162.159.192.4:3854",
    "162.159.192.13:859",
    "162.159.192.5:3581",
    "162.159.195.2:8742",
    "162.159.192.10:934",
    "162.159.192.14:943",
    "162.159.192.17:1387",
    "162.159.192.3:7103",
    "162.159.192.5:854",
    "162.159.192.17:8742",
    "162.159.192.13:7156",
    "162.159.192.9:4198",
    "162.159.192.5:2408",
    "162.159.192.10:2371",
    "162.159.192.9:1010",
    "162.159.192.6:943",
    "162.159.195.4:8742",
    "162.159.192.14:8742",
    "162.159.192.20:1387",
    "162.159.192.15:3138",
    "162.159.195.2:864",
    "162.159.192.11:4233",
    "162.159.195.6:854",
    "162.159.195.9:1014",
    "162.159.198.2:443",
    "162.159.198.1:443",
    "162.159.198.0:443",
    "162.159.192.1:4500",
    "162.159.192.1:2408",
    "162.159.192.1:1701",
    "162.159.192.1:500",
]

# Multiple fallback sources for Clean IP endpoints
CLEAN_IP_SOURCES = [
    # "https://raw.githubusercontent.com/ircfspace/warpendpoint/main/result/warp-ip.txt", # Dead
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/warp.txt",
    "https://www.cloudflare.com/ips-v4",
    "https://raw.githubusercontent.com/MortezaBashsiz/CFScanner/main/config/cf.local.iplist",
]

# Optimized reserved bytes for resistant regions
OPTIMIZED_RESERVED = [
    [84, 146, 56],
    [87, 96, 242],
    [100, 206, 89],
    [98, 157, 152],
    [54, 207, 87],
    [226, 124, 93],
    [22, 18, 221],
    [210, 106, 14],
    [155, 40, 24],
    [60, 173, 68],
]


class ProxyWasher:
    def __init__(self, warp_keys_json: str):
        try:
            parsed = json.loads(warp_keys_json) if warp_keys_json else []
            if not isinstance(parsed, list):
                logger.warning(f"warp_keys_json is not a list, got {type(parsed)}")
                self._warp_keys: List[Dict[str, Any]] = []
            else:
                self._warp_keys = parsed
                if self._warp_keys:
                    logger.info(f"Loaded {len(self._warp_keys)} WARP keys for washing")
                else:
                    # [FIX] Don't log warning here, we will try to generate/fetch later
                    logger.debug("No initial WARP keys configured")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse warp_keys_json: {e}")
            self._warp_keys = []

        self.seen_chains: LRUCache[str, bool] = LRUCache(maxsize=50000)
        self._seen_chains_lock = threading.Lock()
        self._state_lock = threading.Lock()
        # [FIX] Critical: Add asyncio lock for async operations to prevent race conditions
        self._async_state_lock = asyncio.Lock()
        self._clean_ips: List[Tuple[str, int]] = []

        # [FIX] Initialize defaults immediately if not provided
        if not self._warp_keys:
            from configstream.config import AppSettings

            env_keys = AppSettings().WARP_KEY_POOL

            if env_keys and env_keys != "[]":
                try:
                    parsed = json.loads(env_keys)
                except json.JSONDecodeError:
                    # Fallback to comma-separated format
                    parsed = [k.strip() for k in env_keys.split(",") if k.strip()]

                if isinstance(parsed, list):
                    self._warp_keys = parsed

        self.scanner = WarpScannerWorker()
        self.key_gen = KeyGenerator()

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
        [FIX] Critical: Now uses async lock to prevent race conditions with concurrent fetches
        """
        # [FIX] Use async lock for async operations instead of threading.Lock
        async with self._async_state_lock:
            # Check if we need to fetch (inside lock to prevent double-fetching)
            current_keys = self._warp_keys[:]
            current_ips = self._clean_ips[:]

        # --- STRATEGY 0.5: WARP KEYS & IPs FROM SCRAPER (Priority 1) ---
        # We prioritize scraping because it doesn't require a binary
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

                # [FIX] Update state with async lock
                async with self._async_state_lock:
                    if fresh_endpoints:
                        # Normalize to tuples
                        self._clean_ips = []
                        for ep in fresh_endpoints:
                            if isinstance(ep, str):
                                self._clean_ips.append((ep, 2408))
                            else:
                                self._clean_ips.append(ep)
                        logger.info(
                            f"Loaded {len(fresh_endpoints)} clean IPs from Scraper"
                        )

                    if new_keys:
                        self._warp_keys = new_keys
                        logger.info(
                            f"Loaded {len(new_keys)} WARP keys from community sources"
                        )
            except Exception as e:
                logger.warning(f"WARP scraper failed: {e}")

        # --- STRATEGY 0: VWARP SCANNER (Priority 2 if Scraper insufficient) ---
        if not self.clean_ips:
            try:
                vwarp = VwarpTool()
                if await vwarp.is_available():
                    scanned_ips_vwarp = await vwarp.scan_endpoints()
                    if scanned_ips_vwarp:
                        self.clean_ips = scanned_ips_vwarp  # type: ignore[assignment]
                        logger.info(
                            f"Loaded {len(scanned_ips_vwarp)} clean IPs from Vwarp"
                        )
                else:
                    logger.debug("Vwarp binary not found - skipping Vwarp scan.")
            except Exception as e:
                logger.warning(f"Vwarp scanner failed: {e}")

        # --- STRATEGY 1: LEGACY ACTIVE SCANNING ---
        if self.scanner.available and not self.clean_ips:
            try:
                logger.info("Attempting legacy active scan...")
                scanned_ips_legacy = await self.scanner.scan_endpoints(
                    limit=50, timeout=5, max_latency=800
                )

                if scanned_ips_legacy and len(scanned_ips_legacy) >= 5:
                    self.clean_ips = [(ip, 2408) for ip in scanned_ips_legacy]  # type: ignore[misc]
                    logger.info(
                        f"Legacy Scan Success: Using {len(scanned_ips_legacy)} fresh IPs."
                    )
            except Exception as e:
                logger.error(f"Legacy scan failed: {e}")

        # --- STRATEGY 2: STATIC LISTS ---
        if not self.clean_ips:
            logger.info("Starting static list fetch sequence...")
            for source_url in CLEAN_IP_SOURCES:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(source_url)
                        if resp.status_code == 200:
                            lines = [
                                line.strip()
                                for line in resp.text.splitlines()
                                if line.strip() and not line.startswith("#")
                            ]
                            valid_ips = [
                                ip.split("/")[0]
                                for ip in lines
                                if ip.count(".") == 3 and ip[0].isdigit()
                            ]
                            if valid_ips:
                                self.clean_ips = [(ip, 2408) for ip in valid_ips[:100]]
                                logger.info(
                                    f"Fetched {len(valid_ips)} clean IPs from {source_url.split('/')[2]}"
                                )
                                break  # Stop after one success
                except Exception:
                    pass

        # --- STRATEGY 3: DEFAULTS ---
        if not self.clean_ips:
            logger.warning(
                f"All scanners failed. Using {len(DEFAULT_CLEAN_IPS)} default IPs."
            )
            self.clean_ips = [(ip, 2408) for ip in DEFAULT_CLEAN_IPS]

        # --- KEY GENERATION FALLBACK (Last Resort) ---
        # [FIX] If still no keys, try to generate one
        if not self.warp_keys:
            logger.info("No WARP keys found. Attempting to generate a new account...")
            try:
                new_account = await self.key_gen.generate_account()
                if new_account:
                    self.warp_keys = [new_account]
                    logger.info("Successfully generated a new WARP account/key.")
                else:
                    logger.error("Failed to generate WARP account. Washing disabled.")
            except Exception as e:
                logger.error(f"Key generation failed: {e}")

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
                    # Bracketed IPv6: [addr]:port
                    end = host.find("]")
                    ip = host[: end + 1]
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

        if not pool:
            return ("162.159.192.1", 2408)

        hash_val = int(hashlib.sha256(relay_id.encode()).hexdigest(), 16)
        endpoint = pool[hash_val % len(pool)]
        if isinstance(endpoint, str):
            return (endpoint, 2408)
        return endpoint

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
            if key.get("private_key") and key.get("peer_public_key"):
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
        # [FIX] Use 10.x.x.x range for 16M+ unique IPs
        # Bit shift to utilize more of the hash entropy
        octet_2 = (h >> 16) % 255
        octet_3 = (h >> 8) % 255
        octet_4 = (h % 254) + 1  # 1-254
        return f"10.{octet_2}.{octet_3}.{octet_4}/32"

    def get_warp_config(self, seed: str) -> Optional[Dict[str, Any]]:
        """
        [FIX] Generate a WARP WireGuard config for a given seed (used by chaining.py).
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
        return {
            "type": "wireguard",
            "local_address": [unique_ip],
            "private_key": exit_key["private_key"],
            "server": clean_endpoint,
            "server_port": clean_port,
            "peer_public_key": exit_key["peer_public_key"],
            "reserved": reserved,
        }

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

        # Limit revival candidates to prevent explosion (e.g. max 500)
        # [FIX] Prevent infinite recursion: Filter out proxies that are already revived
        candidates = [
            p
            for p in failed_proxies
            if p.protocol != "revived" and not p.details.get("is_revived")
        ][:500]

        for relay in candidates:
            # Basic plausibility check before reviving
            if not relay.address or not relay.port:
                continue

            exit_key = self._get_consistent_exit(relay.id, self.warp_keys)
            if not exit_key:
                continue

            chain_id = f"REVIVE-{relay.id[:8]}"
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

            relay_out["tag"] = f"RELAY-{chain_id}"

            reserved_bytes = self._get_optimized_reserved(chain_id)
            warp_out = {
                "type": "wireguard",
                "tag": chain_id,
                "local_address": [unique_ip],
                "private_key": exit_key["private_key"],
                "server": clean_endpoint,
                "server_port": clean_port,
                "peer_public_key": exit_key["peer_public_key"],
                "reserved": reserved_bytes,
                "detour": relay_out["tag"],
            }

            # We bundle BOTH outbounds into the proxy details for special handling
            # FIX: Serialize relay object to prevent JSON errors
            # Use the canonical Pydantic method for serialization.
            origin_dict = relay.model_dump(mode="json")

            revived_proxy = Proxy(
                config=f"revived://{relay.address}",  # Dummy config
                protocol="revived",  # Special protocol
                address=clean_endpoint,
                port=clean_port,
                uuid=chain_id,
                remarks=f"Revived {relay.protocol.upper()}",
                details={
                    "chain_outbounds": [relay_out, warp_out],  # The full chain
                    "is_revived": True,
                    "use_vwarp": use_vwarp,
                    "origin_proxy": origin_dict,
                },
            )

            revived_candidates.append(revived_proxy)
            revived_count += 1

            if stats:
                if use_vwarp:
                    stats.vwarp_attempts += 1
                else:
                    stats.warp_attempts += 1

        return revived_candidates, revived_count

    def wash_batch(
        self, proxies: List[Proxy], stats: Optional[PipelineStats] = None
    ) -> Tuple[List[Dict[str, Any]], Set[str], Dict[str, int]]:
        """
        Legacy/Standard Washing: Process WORKING proxies to create chains.
        """
        washed_outbounds: List[Dict[str, Any]] = []
        washed_ids: Set[str] = set()
        skip_reasons: Dict[str, int] = {}

        keys = self.warp_keys
        if not keys:
            return washed_outbounds, washed_ids, skip_reasons

        candidates = [p for p in proxies if p.is_working]

        target_exit = ProxyStub("US", 37.09, -95.71, "wireguard")
        origin_country = AppSettings().OPTIMAL_RELAY_ORIGIN

        for i, relay in enumerate(candidates):
            if stats:
                stats.vwarp_attempts += 1

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
                    relay_stub = ProxyStub(relay.country_code, 0.0, 0.0, relay.protocol)
                    relay_stub.lat, relay_stub.lon = COUNTRIES[relay.country_code]
                    res = find_optimal_relay(origin_country, target_exit, [relay_stub])
                    if isinstance(res, dict) and "relay" in res:
                        if float(res.get("total_distance", 99999)) < 15000:
                            is_optimal = True
            except Exception:
                pass

            exit_tag_prefix = "🛡️⚡ Optimal" if is_optimal else "🛡️ Secure"
            exit_tag = f"{exit_tag_prefix}-{relay.country_code}-{i+1}"

            reserved_bytes = self._get_optimized_reserved(chain_id)
            warp_out = {
                "type": "wireguard",
                "tag": exit_tag,
                "local_address": [unique_ip],
                "private_key": exit_key["private_key"],
                "server": clean_endpoint,
                "server_port": clean_port,
                "peer_public_key": exit_key["peer_public_key"],
                "reserved": reserved_bytes,
                "detour": relay_tag,
            }

            washed_outbounds.append(relay_out)
            # Add metadata for process tracking
            warp_out["_process"] = "washed"
            washed_outbounds.append(warp_out)
            washed_ids.add(relay.id)

            if stats:
                stats.vwarp_success += 1

        return washed_outbounds, washed_ids, skip_reasons
