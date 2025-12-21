import json
import hashlib
import logging
import threading
import os
import httpx
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
        # --- STRATEGY 0.5: WARP KEYS & IPs FROM SCRAPER (Priority 1) ---
        # We prioritize scraping because it doesn't require a binary
        if not self.warp_keys or not self.clean_ips:
            try:
                scraper = WarpScraper()
                scraped_keys = await scraper.scrape_warp_sources()

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

        # --- STRATEGY 0: VWARP SCANNER (Priority 2 if Scraper insufficient) ---
        if not self.clean_ips:
            try:
                vwarp = VwarpTool()
                if await vwarp.is_available():
                    scanned_ips_vwarp = await vwarp.scan_endpoints()
                    if scanned_ips_vwarp:
                        self.clean_ips = scanned_ips_vwarp  # type: ignore[assignment]
                        logger.info(f"Loaded {len(scanned_ips_vwarp)} clean IPs from Vwarp")
                        return
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
                    return
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
                                self.clean_ips = valid_ips[:100]
                                logger.info(
                                    f"Fetched {len(valid_ips)} clean IPs from {source_url.split('/')[2]}"
                                )
                                return
                except Exception:
                    pass

        # --- STRATEGY 3: DEFAULTS ---
        if not self.clean_ips:
            logger.warning(
                f"All scanners failed. Using {len(DEFAULT_CLEAN_IPS)} default IPs."
            )
            self.clean_ips = [(ip, 2408) for ip in DEFAULT_CLEAN_IPS]  # type: ignore[misc]

    def _get_clean_endpoint(self, relay_id: str) -> Any:
        pool = self.clean_ips
        if not pool:
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

    def wash_failed(
        self,
        failed_proxies: List[Proxy],
        stats: Optional[PipelineStats] = None,
        use_vwarp: bool = False
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
        candidates = failed_proxies[:500]

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

            warp_out = {
                "type": "wireguard",
                "tag": chain_id,
                "local_address": [unique_ip],
                "private_key": exit_key["private_key"],
                "server": clean_endpoint,
                "server_port": clean_port,
                "peer_public_key": exit_key["peer_public_key"],
                "detour": relay_out["tag"],
            }

            # We bundle BOTH outbounds into the proxy details for special handling
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
                    "origin_proxy": relay
                }
            )

            revived_candidates.append(revived_proxy)
            revived_count += 1

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
        origin_country = os.environ.get("OPTIMAL_RELAY_ORIGIN", "IR")

        for i, relay in enumerate(candidates):
            if stats:
                stats.vwarp_attempts += 1

            exit_key = self._get_consistent_exit(relay.id, keys)
            if not exit_key:
                skip_reasons["invalid_warp_key"] = skip_reasons.get("invalid_warp_key", 0) + 1
                continue

            chain_id = "CHAIN-{cc}-{rid}-{eid}".format(
                cc=relay.country_code,
                rid=relay.id[:6],
                eid=exit_key.get("id", "00")[:4],
            )

            with self._seen_chains_lock:
                if chain_id in self.seen_chains:
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
            # Add metadata for process tracking
            warp_out["_process"] = "washed"
            washed_outbounds.append(warp_out)
            washed_ids.add(relay.id)

            if stats:
                stats.vwarp_success += 1

        return washed_outbounds, washed_ids, skip_reasons
