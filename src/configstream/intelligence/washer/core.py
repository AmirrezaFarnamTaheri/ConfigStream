import json
import hashlib
import logging
import threading
import os
import httpx
import asyncio
import time
from typing import List, Dict, Optional, Set, Any, Tuple
from cachetools import LRUCache

from ...models import Proxy
from ...converters import to_singbox_outbound
from ...workers.scanner import WarpScannerWorker
from .warp_scraper import WarpScraper
from ...tools.vwarp import VwarpTool
from ..chaining import find_optimal_relay, ProxyStub, COUNTRIES
from ...pipeline_core.stats import PipelineStats

logger = logging.getLogger(__name__)

# Static fallback if fetch fails
DEFAULT_CLEAN_IPS = ["162.159.192.1", "162.159.193.10", "162.159.195.5"]

# Multiple fallback sources for Clean IP endpoints
CLEAN_IP_SOURCES = [
    "https://raw.githubusercontent.com/ircfspace/warpendpoint/main/result/warp-ip.txt",
    "https://www.cloudflare.com/ips-v4",
    "https://raw.githubusercontent.com/MortezaBashsiz/CFScanner/main/config/cf.local.iplist",
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
                    logger.warning("No WARP keys configured - washing will be disabled")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse warp_keys_json: {e}")
            self._warp_keys = []

        self.seen_chains: LRUCache[str, bool] = LRUCache(maxsize=50000)
        self._seen_chains_lock = threading.Lock()
        # [FIX] Add lock to protect state modifications for thread-safety
        # Prevents race conditions between async fetch_clean_ips() and sync wash_batch()
        self._state_lock = threading.Lock()
        self._clean_ips: List[str] = []

        self.scanner = WarpScannerWorker()

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
    def clean_ips(self) -> List[str]:
        """Thread-safe read of clean_ips."""
        with self._state_lock:
            return self._clean_ips[:]

    @clean_ips.setter
    def clean_ips(self, value: List[str]) -> None:
        """Thread-safe write of clean_ips."""
        with self._state_lock:
            self._clean_ips = value

    async def fetch_clean_ips(self) -> None:
        """
        Fetches the latest clean IPs for WARP endpoints.
        """

        # --- STRATEGY 0: VWARP SCANNER ---
        try:
            vwarp = VwarpTool()
            scanned_ips_vwarp = await vwarp.scan_endpoints()
            if scanned_ips_vwarp:
                self.clean_ips = scanned_ips_vwarp  # type: ignore[assignment]
                logger.info(f"Loaded {len(scanned_ips_vwarp)} clean IPs from Vwarp")
                return
        except Exception as e:
            logger.warning(f"Vwarp scanner failed: {e}")

        # --- STRATEGY 0.5: WARP KEYS FROM SCRAPER ---
        if not self.warp_keys:
            logger.info("No WARP keys configured, trying community sources...")
            try:
                # [FIX] Use class method
                scraper = WarpScraper()
                scraped_keys = await scraper.scrape_warp_sources()

                # [FIX] Capture scraped endpoints from the scraper
                fresh_endpoints = scraper.get_scraped_endpoints()
                if fresh_endpoints:
                    self.clean_ips = fresh_endpoints
                    logger.info(f"Loaded {len(fresh_endpoints)} clean IPs from Scraper")

                new_keys = []
                for p in scraped_keys:
                    key_dict = {
                        "private_key": p.details.get("private_key"),
                        "peer_public_key": p.details.get("peer_public_key"),
                        "id": p.uuid,
                    }
                    if key_dict["private_key"] and key_dict["peer_public_key"]:
                        new_keys.append(key_dict)

                if new_keys:
                    self.warp_keys = new_keys
                    logger.info(
                        f"Loaded {len(new_keys)} WARP keys from community sources"
                    )
            except Exception as e:
                logger.warning(f"WARP scraper failed: {e}")

        # --- STRATEGY 1: LEGACY ACTIVE SCANNING ---
        if self.scanner.available:
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
                    return
            except Exception as e:
                logger.error(f"Legacy scan failed: {e}")

        # --- STRATEGY 2: STATIC LISTS ---
        logger.info("Starting static list fetch sequence...")
        for source_url in CLEAN_IP_SOURCES:
            max_retries = 2
            backoff_factor = 2
            base_delay = 1

            for attempt in range(max_retries):
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
                                self.clean_ips = valid_ips[:100]
                                logger.info(
                                    f"Fetched {len(valid_ips)} clean IPs from {source_url.split('/')[2]}"
                                )
                                return
                        else:
                            logger.debug(
                                f"Fetch failed from {source_url}: {resp.status_code}"
                            )
                except Exception:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (backoff_factor**attempt))

        # --- STRATEGY 3: DEFAULTS ---
        logger.warning(
            f"All scanners failed. Using {len(DEFAULT_CLEAN_IPS)} default IPs."
        )
        self.clean_ips = [(ip, 2408) for ip in DEFAULT_CLEAN_IPS]  # type: ignore[misc]

    def _get_clean_endpoint(self, relay_id: str) -> Any:
        # Use property access for thread safety
        pool = self.clean_ips
        if not pool:
            # Revert to default
            pool = DEFAULT_CLEAN_IPS

        if not pool:
            return "162.159.192.1"

        hash_val = int(hashlib.sha256(relay_id.encode()).hexdigest(), 16)
        return pool[hash_val % len(pool)]

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

    def _generate_deterministic_ip(self, seed: str) -> str:
        h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        octet_3 = (h // 250) % 250
        octet_4 = (h % 250) + 2
        return f"172.16.{octet_3}.{octet_4}/32"

    def get_warp_config(self, seed_id: str) -> Optional[Dict[str, Any]]:
        # Use property access for thread safety
        keys = self.warp_keys
        if not keys:
            return None

        identity = self._get_consistent_exit(seed_id, keys)
        if not identity:
            return None

        endpoint = self._get_clean_endpoint(seed_id)

        # Handle tuple endpoint (IP, Port)
        if isinstance(endpoint, tuple) and len(endpoint) == 2:
            clean_endpoint, clean_port = endpoint
        else:
            clean_endpoint = str(endpoint)
            try:
                clean_port = int(os.environ.get("WARP_PORT", "2408"))
            except (ValueError, TypeError):
                clean_port = 2408

        return {
            "type": "wireguard",
            "server": clean_endpoint,
            "server_port": clean_port,
            "local_address": [self._generate_deterministic_ip(seed_id)],
            "private_key": identity["private_key"],
            "peer_public_key": identity["peer_public_key"],
            "mtu": 1280,
        }

    def wash_batch(
        self, proxies: List[Proxy], stats: Optional[PipelineStats] = None
    ) -> Tuple[List[Dict[str, Any]], Set[str], Dict[str, int]]:
        """
        Process a batch of proxies, identifying 'washable' candidates
        and generating unique chains.
        """
        washed_outbounds: List[Dict[str, Any]] = []
        washed_ids: Set[str] = set()
        skip_reasons: Dict[str, int] = {}

        keys = self.warp_keys
        if not keys:
            logger.info("Washing skipped: WARP_KEY_POOL not configured")
            return washed_outbounds, washed_ids, skip_reasons

        working_count = sum(1 for p in proxies if p.is_working)
        if working_count == 0:
            logger.warning("Washing skipped: No working proxies available")
            return washed_outbounds, washed_ids, skip_reasons

        candidates = [p for p in proxies if p.is_working]
        logger.info(f"Washing {len(candidates)} proxies through WARP...")

        target_exit = ProxyStub("US", 37.09, -95.71, "wireguard")
        origin_country = os.environ.get("OPTIMAL_RELAY_ORIGIN", "IR")

        for i, relay in enumerate(candidates):
            # [METRICS] Increment Attempts
            if stats:
                stats.vwarp_attempts += 1

            exit_key = self._get_consistent_exit(relay.id, keys)
            if not exit_key:
                skip_reasons["invalid_warp_key"] = (
                    skip_reasons.get("invalid_warp_key", 0) + 1
                )
                continue

            chain_id = "CHAIN-{cc}-{rid}-{eid}".format(
                cc=relay.country_code,
                rid=relay.id[:6],
                eid=exit_key.get("id", "00")[:4],
            )

            with self._seen_chains_lock:
                if chain_id in self.seen_chains:
                    skip_reasons["duplicate_chain"] = (
                        skip_reasons.get("duplicate_chain", 0) + 1
                    )
                    continue
                self.seen_chains[chain_id] = True

            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                skip_reasons["conversion_failed"] = (
                    skip_reasons.get("conversion_failed", 0) + 1
                )
                continue

            relay_tag = f"RELAY-{chain_id}"
            relay_out["tag"] = relay_tag

            endpoint_data = self._get_clean_endpoint(relay.id)

            # Handle both string IPs (legacy) and tuple (ip, port) (new Vwarp)
            if isinstance(endpoint_data, tuple) and len(endpoint_data) == 2:
                clean_endpoint, clean_port = endpoint_data
            else:
                clean_endpoint = str(endpoint_data)
                # Fallback to env port or default
                clean_port_str = os.environ.get("WARP_PORT", "2408")
                try:
                    clean_port = int(clean_port_str)
                except (ValueError, TypeError):
                    clean_port = 2408

            if not (1 <= clean_port <= 65535):
                skip_reasons["invalid_endpoint"] = (
                    skip_reasons.get("invalid_endpoint", 0) + 1
                )
                continue

            unique_ip = self._generate_deterministic_ip(chain_id)

            is_optimal = False
            try:
                # FIX: Use country_code (e.g., "US") not country (e.g., "United States")
                # COUNTRIES dict is keyed by ISO country codes
                if relay.country_code and relay.country_code in COUNTRIES:
                    relay_stub = ProxyStub(relay.country_code, 0.0, 0.0, relay.protocol)
                    relay_stub.lat, relay_stub.lon = COUNTRIES[relay.country_code]
                    res = find_optimal_relay(origin_country, target_exit, [relay_stub])
                    if isinstance(res, dict) and "relay" in res:
                        total_distance = res.get("total_distance", 99999)
                        # Ensure float comparison
                        if float(total_distance) < 15000:
                            is_optimal = True
            except Exception:
                pass

            exit_tag_prefix = "🛡️⚡ Optimal" if is_optimal else "🛡️ Secure"
            exit_tag = f"{exit_tag_prefix}-{relay.country_code}-{i+1}"

            warp_out = {
                "type": "wireguard",
                "tag": exit_tag,
                "local_address": [unique_ip],
                "private_key": exit_key["private_key"],
                "server": clean_endpoint,
                "server_port": clean_port,
                "peer_public_key": exit_key["peer_public_key"],
                "detour": relay_tag,
            }

            washed_outbounds.append(relay_out)
            washed_outbounds.append(warp_out)
            washed_ids.add(relay.id)

            # [METRICS] Increment Success
            if stats:
                stats.vwarp_success += 1

        conversion_failures = len(candidates) - len(washed_ids)

        logger.info(
            f"Washing complete: {len(washed_ids)}/{len(candidates)} proxies washed. "
            f"Conversion Failures: {conversion_failures}. "
            f"Clean IPs: {len(self.clean_ips)}"
        )

        return washed_outbounds, washed_ids, skip_reasons
