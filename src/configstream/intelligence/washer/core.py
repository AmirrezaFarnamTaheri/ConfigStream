import json
import hashlib
import logging
import threading
import os
import httpx
import asyncio
from typing import List, Dict, Optional, Set, Any, Tuple

from ...models import Proxy
from ...converters import to_singbox_outbound
from ...workers.scanner import WarpScannerWorker
from .warp_scraper import scrape_warp_sources
from ..chaining import find_optimal_relay, ProxyStub, COUNTRIES

logger = logging.getLogger(__name__)

# Static fallback if fetch fails
DEFAULT_CLEAN_IPS = ["162.159.192.1", "162.159.193.10", "162.159.195.5"]

# Multiple fallback sources for Clean IP endpoints
# Priority order: first working source wins
CLEAN_IP_SOURCES = [
    # Primary: ircfspace warpendpoint (new location)
    "https://raw.githubusercontent.com/ircfspace/warpendpoint/main/result/warp-ip.txt",
    # Fallback 1: Cloudflare official ranges (general CDN IPs)
    "https://www.cloudflare.com/ips-v4",
    # Fallback 2: Alternative community-maintained list
    "https://raw.githubusercontent.com/MortezaBashsiz/CFScanner/main/config/cf.local.iplist",
]


class ProxyWasher:
    def __init__(self, warp_keys_json: str):
        try:
            parsed = json.loads(warp_keys_json) if warp_keys_json else []
            # Validate that it's a list
            if not isinstance(parsed, list):
                logger.warning(f"warp_keys_json is not a list, got {type(parsed)}")
                self.warp_keys = []
            else:
                self.warp_keys = parsed
                if self.warp_keys:
                    logger.info(f"Loaded {len(self.warp_keys)} WARP keys for washing")
                else:
                    logger.warning("No WARP keys configured - washing will be disabled")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse warp_keys_json: {e}")
            self.warp_keys = []
        self.seen_chains: Set[str] = set()
        self._seen_chains_lock = threading.Lock()
        self.clean_ips: List[str] = []
        # Audit: Limit seen chains memory usage
        self.max_seen_chains = 100000

        # Initialize the Active Scanner
        self.scanner = WarpScannerWorker()

    async def fetch_clean_ips(self) -> None:
        """
        Fetches the latest clean IPs for WARP endpoints.
        Strategy:
        1. Active Scanning (High Performance, Local Latency)
        2. Static Lists (Reliability Fallback)
        3. Hardcoded Defaults (Last Resort)
        """

        # --- STRATEGY 0: WARP SCRAPER (NEW FIRST FALLBACK) ---
        if not self.warp_keys:
            logger.info("No WARP keys configured, trying community sources...")
            try:
                scraped_keys = await scrape_warp_sources()
                if scraped_keys:
                    self.warp_keys = scraped_keys
                    logger.info(
                        f"Loaded {len(scraped_keys)} WARP keys from community sources"
                    )
            except Exception as e:
                logger.warning(f"WARP scraper failed: {e}")

        # --- STRATEGY 1: ACTIVE SCANNING ---
        # Only run if the binary is available
        if self.scanner.available:
            try:
                # Scan for 50 fresh IPs with a tight 5s timeout to keep pipeline fast
                logger.info("Attempting active scan for fresh WARP endpoints...")
                scanned_ips = await self.scanner.scan_endpoints(
                    limit=50, timeout=5, max_latency=800
                )

                # We need at least a few IPs to consider the scan "successful"
                if scanned_ips and len(scanned_ips) >= 5:
                    self.clean_ips = scanned_ips
                    logger.info(
                        f"Active Scan Success: Using {len(self.clean_ips)} fresh IPs "
                        f"(Static sources skipped). Top: {self.clean_ips[:3]}"
                    )
                    return  # SUCCESS - Exit early, skip static lists
                else:
                    logger.warning(
                        f"Active scan returned insufficient IPs ({len(scanned_ips)}). "
                        "Falling back to static lists."
                    )
            except Exception as e:
                logger.error(f"Active scan failed unexpectedly: {e}")
        else:
            logger.debug(
                "Scanner binary not available/configured. Skipping active scan."
            )

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
                            # Filter valid IPs (IPv4 only for now)
                            lines = [
                                line.strip()
                                for line in resp.text.splitlines()
                                if line.strip() and not line.startswith("#")
                            ]
                            # Basic validation: must look like IPv4
                            valid_ips = [
                                ip.split("/")[0]  # Handle CIDR notation
                                for ip in lines
                                if ip.count(".") == 3 and ip[0].isdigit()
                            ]
                            if valid_ips:
                                self.clean_ips = valid_ips[:100]  # Limit pool size
                                logger.info(
                                    "Fetched %d clean IPs from %s",
                                    len(self.clean_ips),
                                    source_url.split("/")[2],  # Domain only
                                )
                                return  # Success - exit all loops
                        else:
                            logger.debug(
                                f"Clean IPs fetch from {source_url} returned {resp.status_code}"
                            )
                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (backoff_factor**attempt)
                        await asyncio.sleep(delay)
                    else:
                        logger.debug(
                            f"Source {source_url} failed after {max_retries} attempts: {e}"
                        )

        # --- STRATEGY 3: DEFAULTS ---
        logger.warning(
            f"All Clean IP sources failed. Using {len(DEFAULT_CLEAN_IPS)} default IPs."
        )
        self.clean_ips = DEFAULT_CLEAN_IPS.copy()

    def _get_clean_endpoint(self, relay_id: str) -> str:
        """Deterministically selects a clean IP based on proxy ID."""
        pool = self.clean_ips if self.clean_ips else DEFAULT_CLEAN_IPS
        if not pool:
            logger.critical(
                "Clean IP pool is empty, falling back to a single default IP."
            )
            return DEFAULT_CLEAN_IPS[0] if DEFAULT_CLEAN_IPS else "162.159.192.1"

        # Consistent hashing so the same proxy always gets the same endpoint (stability)
        hash_val = int(hashlib.sha256(relay_id.encode()).hexdigest(), 16)
        return pool[hash_val % len(pool)]

    def _get_consistent_exit(
        self, relay_id: str, exit_pool: List[Dict]
    ) -> Optional[Dict]:
        """
        Selects an exit node deterministically based on the relay's ID.
        Acts as a 'Stateless Cache'.
        """
        if not exit_pool:
            return None

        # Create a deterministic index from the Relay ID
        hash_val = int(hashlib.sha256(relay_id.encode()).hexdigest(), 16)
        index = hash_val % len(exit_pool)
        return exit_pool[index]

    def get_warp_config(self, seed_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns a configuration dictionary for a WARP WireGuard outbound.
        Used by external modules (like chaining) to wrap connections.
        """
        if not self.warp_keys:
            return None

        # 1. Get consistent credentials (reuse existing logic)
        identity = self._get_consistent_exit(seed_id, self.warp_keys)
        if not identity:
            return None

        # 2. Get clean endpoint (reuse existing logic)
        endpoint = self._get_clean_endpoint(seed_id)

        # 3. Get Port
        try:
            port = int(os.environ.get("WARP_PORT", "2408"))
        except (ValueError, TypeError):
            port = 2408

        # 4. Return the specific config needed for Sing-box
        return {
            "type": "wireguard",
            "server": endpoint,
            "server_port": port,
            "local_address": [
                f"172.16.{hash(seed_id) % 250}.2/32"
            ],  # Simplified unique IP generation
            "private_key": identity["private_key"],
            "peer_public_key": identity["peer_public_key"],
            "mtu": 1280,  # Important for chains to avoid fragmentation
        }

    def wash_batch(self, proxies: List[Proxy]) -> Tuple[List[Dict[str, Any]], Set[str]]:
        """
        Process a batch of proxies, identifying 'washable' candidates
        and generating unique chains.

        Returns:
            - List of Sing-box outbound objects (Relay + Exit)
            - Set of Proxy IDs that were successfully washed
        """
        washed_outbounds: List[Dict[str, Any]] = []
        washed_ids: Set[str] = set()

        # Early exit with clear logging
        if not self.warp_keys:
            logger.info("Washing skipped: WARP_KEY_POOL not configured")
            return washed_outbounds, washed_ids

        working_count = sum(1 for p in proxies if p.is_working)
        if working_count == 0:
            logger.warning(
                "Washing skipped: No working proxies available (upstream testing failed)"
            )
            return washed_outbounds, washed_ids

        # 1. Identify Candidates
        candidates = [p for p in proxies if p.is_working and self.warp_keys]
        logger.info(
            f"Washing {len(candidates)} proxies through WARP "
            f"(Total Working: {working_count}, Key Pool: {len(self.warp_keys)})"
        )
        if len(candidates) > 0:
            logger.info(f"Washer: Attempting to revive {len(candidates)} proxies...")

        skip_reasons: Dict[str, int] = {}

        # --- NEW: Use Geodesic Optimization Target ---
        # Assume US target for checking optimal routing (as per audit snippet)
        target_exit = ProxyStub("US", 37.09, -95.71, "wireguard")

        for i, relay in enumerate(candidates):
            # 2. Select the "Soap" (Exit Node)
            exit_key = self._get_consistent_exit(relay.id, self.warp_keys)
            if (
                not exit_key
                or not exit_key.get("private_key")
                or not exit_key.get("peer_public_key")
            ):
                skip_reasons["invalid_warp_key"] = (
                    skip_reasons.get("invalid_warp_key", 0) + 1
                )
                logger.debug(
                    f"Skipping proxy {relay.id[:8]}: invalid WARP key (missing private or public key)"
                )
                continue

            # 3. Generate Deterministic Chain ID
            chain_id = "CHAIN-{cc}-{rid}-{eid}".format(
                cc=relay.country_code,
                rid=relay.id[:6],
                eid=exit_key.get("id", "00")[:4],
            )

            # Thread-safe check-then-act for deduplication
            with self._seen_chains_lock:
                if chain_id in self.seen_chains:
                    skip_reasons["duplicate_chain"] = (
                        skip_reasons.get("duplicate_chain", 0) + 1
                    )
                    continue  # Skip duplicates

                # Prune if too large
                if len(self.seen_chains) > self.max_seen_chains:
                    self.seen_chains.clear()
                    logger.warning("Flushed seen_chains cache (limit exceeded)")

                self.seen_chains.add(chain_id)

            # 4. Construct the Chain Objects
            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                skip_reasons["conversion_failed"] = (
                    skip_reasons.get("conversion_failed", 0) + 1
                )
                logger.debug(
                    f"Skipping proxy {relay.id[:8]}: conversion to singbox failed"
                )
                continue

            relay_tag = f"RELAY-{chain_id}"
            relay_out["tag"] = relay_tag

            # --- NEW: Use Clean IP ---
            clean_endpoint = self._get_clean_endpoint(relay.id)
            clean_port_str = os.environ.get("WARP_PORT", "2408")

            # Validate endpoint/port before emitting outbound
            if not isinstance(clean_endpoint, str) or not clean_endpoint:
                skip_reasons["invalid_endpoint"] = (
                    skip_reasons.get("invalid_endpoint", 0) + 1
                )
                logger.debug(
                    f"Skipping proxy {relay.id[:8]}: invalid clean endpoint '{clean_endpoint}'"
                )
                continue
            try:
                clean_port = int(clean_port_str)
                if not (1 <= clean_port <= 65535):
                    raise ValueError("port out of range")
            except Exception:
                skip_reasons["invalid_endpoint"] = (
                    skip_reasons.get("invalid_endpoint", 0) + 1
                )
                logger.debug(
                    f"Skipping proxy {relay.id[:8]}: invalid clean port '{clean_port_str}'"
                )
                continue

            # [FIX] Generate Unique Local IP
            h = int(hashlib.sha256(chain_id.encode()).hexdigest(), 16)
            octet_2 = (h >> 8) % 255
            octet_3 = (h % 250) + 2
            unique_ip = f"172.16.{octet_2}.{octet_3}/32"

            # --- NEW: Geodesic Optimization Tagging ---
            is_optimal = False
            try:
                if relay.country in COUNTRIES:
                    relay_stub = ProxyStub(relay.country, 0.0, 0.0, relay.protocol)
                    relay_stub.lat, relay_stub.lon = COUNTRIES[relay.country]

                    # Check optimization for "IR" origin (example high censorship) to US
                    res = find_optimal_relay("IR", target_exit, [relay_stub])
                    if isinstance(res, dict) and "relay" in res:
                        # If the penalty wasn't high enough to exclude it (it returns best of list, so we check distance)
                        # Heuristic: < 15000km is decent for IR -> US via EU
                        total_distance = res.get("total_distance", 99999)
                        try:
                            if float(total_distance) < 15000:
                                is_optimal = True
                        except (TypeError, ValueError):
                            logger.debug(
                                f"Non-numeric total_distance for relay {relay.id}: {total_distance}"
                            )
            except Exception as e:
                logger.debug(
                    f"Could not determine optimality for relay {relay.id}: {e}"
                )

            exit_tag_prefix = "🛡️ Secure"
            if is_optimal:
                exit_tag_prefix = "🛡️⚡ Optimal"

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
            logger.debug(
                f"Created washed chain {chain_id}: {relay_tag} -> {exit_tag} "
                f"(Clean IP: {clean_endpoint})"
            )
            # Log successful wash event
            logger.debug(
                f"Washer: Successfully revived proxy {relay.id[:8]} -> {exit_tag}"
            )

        # Calculate detailed washing statistics
        conversion_failures = len(candidates) - len(washed_ids)

        # Enhanced logging for clean IPs usage
        clean_ip_usage: Dict[str, int] = {}
        for out in washed_outbounds:
            if out.get("type") == "wireguard" and "server" in out:
                srv = out["server"]
                clean_ip_usage[srv] = clean_ip_usage.get(srv, 0) + 1

        logger.info(
            f"Washing complete: {len(washed_ids)}/{len(candidates)} proxies washed "
            f"(conversion_failures={conversion_failures}, "
            f"warp_pool_size={len(self.warp_keys)}, "
            f"clean_ips={len(self.clean_ips)}). "
            f"Clean IP Usage: {json.dumps(clean_ip_usage)}. "
            f"Skip reasons: {json.dumps(skip_reasons)}"
        )

        if conversion_failures > 0:
            logger.debug(
                f"Washing conversion failures details: {json.dumps(skip_reasons)}"
            )

        return washed_outbounds, washed_ids
