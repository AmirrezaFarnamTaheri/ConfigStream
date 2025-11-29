"""
Proxy Washing and Chaining Intelligence.
Handles the logic for creating proxy chains and washing proxies through WARP/WireGuard.
"""

import json
import hashlib
import logging
import threading
import os
import httpx
from typing import List, Dict, Optional, Set, Any, Tuple
from ..models import Proxy
from ..converters import to_singbox_outbound

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

    async def fetch_clean_ips(self) -> None:
        """
        Fetches the latest clean IPs for WARP endpoints with retry logic.
        Tries multiple sources in priority order.
        """
        import asyncio

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

        # All sources failed - use defaults
        logger.warning(
            f"All Clean IP sources failed. Using {len(DEFAULT_CLEAN_IPS)} default IPs."
        )
        self.clean_ips = DEFAULT_CLEAN_IPS.copy()

    def _get_clean_endpoint(self, relay_id: str) -> str:
        """Deterministically selects a clean IP based on proxy ID."""
        pool = self.clean_ips if self.clean_ips else DEFAULT_CLEAN_IPS
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
        # Current strategy: when WARP keys are available, wash ALL working
        # proxies rather than relying solely on tags. Tags are still useful
        # for downstream labeling but not a hard requirement here.
        candidates = [p for p in proxies if p.is_working and self.warp_keys]
        logger.info(f"Washing {len(candidates)} proxies through WARP")

        for i, relay in enumerate(candidates):
            # 2. Select the "Soap" (Exit Node)
            exit_key = self._get_consistent_exit(relay.id, self.warp_keys)
            if not exit_key or "private_key" not in exit_key:
                logger.debug(f"Skipping proxy {relay.id[:8]}: invalid WARP key")
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
                    continue  # Skip duplicates

                # Prune if too large (simple flush for now, LRU is better but heavier)
                if len(self.seen_chains) > self.max_seen_chains:
                    self.seen_chains.clear()
                    logger.warning("Flushed seen_chains cache (limit exceeded)")

                self.seen_chains.add(chain_id)

            # 4. Construct the Chain Objects
            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                logger.debug(
                    f"Skipping proxy {relay.id[:8]}: conversion to singbox failed"
                )
                continue

            relay_tag = f"RELAY-{chain_id}"
            relay_out["tag"] = relay_tag

            # --- NEW: Use Clean IP ---
            clean_endpoint = self._get_clean_endpoint(relay.id)
            clean_port = int(os.environ.get("WARP_PORT", "2408"))

            # [FIX] Generate Unique Local IP for WireGuard to avoid collisions
            # 172.16.X.Y (IPv4) or fd00::X:Y (IPv6)
            h = int(hashlib.sha256(chain_id.encode()).hexdigest(), 16)

            # Support IPv6 environment if needed (Audit recommendation)
            # We generate both or detect environment? Since we are generating config,
            # assume IPv4 is standard for now but provide unique local V6 just in case.
            # But Singbox WireGuard outbound usually takes one local address.
            # Let's stick to IPv4 but ensure range is safe.

            octet_2 = (h >> 8) % 255
            octet_3 = (h % 250) + 2  # Avoid .0 and .1
            unique_ip = f"172.16.{octet_2}.{octet_3}/32"

            exit_tag = f"🛡️ Secure-{relay.country_code}-{i+1}"
            warp_out = {
                "type": "wireguard",
                "tag": exit_tag,
                "local_address": [unique_ip],
                "private_key": exit_key["private_key"],
                "server": clean_endpoint,  # Replaces hardcoded 162.159...
                "server_port": clean_port,
                "peer_public_key": exit_key.get(
                    "peer_public_key", "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="
                ),
                "detour": relay_tag,  # <--- The Link
                # Inject keepalive to maintain NAT mapping
                "keepalive_interval": 20,
            }

            washed_outbounds.append(relay_out)
            washed_outbounds.append(warp_out)
            washed_ids.add(relay.id)

        # Calculate detailed washing statistics
        conversion_failures = len(candidates) - len(washed_ids)

        logger.info(
            f"Washing complete: {len(washed_ids)}/{len(candidates)} proxies washed "
            f"(conversion_failures={conversion_failures}, "
            f"warp_pool_size={len(self.warp_keys)}, "
            f"clean_ips={len(self.clean_ips)})"
        )
        return washed_outbounds, washed_ids


def create_chain(
    relay: Proxy, exit_node: Proxy, tag_prefix: str
) -> List[Dict[str, Any]]:
    """Helper to generate Sing-box outbound objects for a chain."""
    relay_out = to_singbox_outbound(relay)
    exit_out = to_singbox_outbound(exit_node)

    if not relay_out or not exit_out:
        return []

    relay_tag = f"{tag_prefix}-RELAY-{relay.id[:6]}"
    exit_tag = f"{tag_prefix}-EXIT-{exit_node.country}-{exit_node.id[:6]}"

    relay_out["tag"] = relay_tag
    exit_out["tag"] = exit_tag
    exit_out["detour"] = relay_tag  # The chaining magic

    return [relay_out, exit_out]


def _deterministic_select(pool: List[Proxy], seed: str) -> Proxy:
    """
    Select a proxy from pool deterministically based on seed string.
    This ensures reproducible builds - same input produces same output.
    """
    if not pool:
        raise ValueError("Cannot select from empty pool")

    # Use SHA-256 for consistent hashing
    hash_val = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return pool[hash_val % len(pool)]


def generate_smart_chains(proxies: List[Proxy]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate intelligent proxy chains based on network topology.
    Returns a dict of chain types to list of outbound objects.
    """
    chains: Dict[str, List[Dict[str, Any]]] = {
        "intranet": [],
        "ipv6": [],
        "streamer": [],
        "experimental": [],  # Hysteria->VMess
    }

    # Statistics tracking
    stats = {"attempted": 0, "succeeded": 0, "failed": 0}

    # 1. Categorize Resources
    relays_ir = [p for p in proxies if p.country_code == "IR" and p.is_working]
    relays_dual_stack = [
        p for p in proxies if p.is_working and ":" not in p.address
    ]  # Approx IPv4
    relays_fast = [
        p for p in proxies if p.is_working and p.protocol in ["hysteria2", "tuic"]
    ]

    exits_ipv6 = [p for p in proxies if p.is_working and ":" in p.address]
    exits_streaming = [
        p for p in proxies if p.is_working and p.country_code in ["US", "GB", "DE"]
    ]
    exits_standard = [
        p
        for p in proxies
        if p.is_working and p.protocol in ["vmess", "shadowsocks", "trojan"]
    ]

    # --- CHAIN 1: THE INTRANET BRIDGE (Gold Standard) - FIXED ---
    # Sort foreign exits by latency before selection
    foreign_exits = sorted(
        [p for p in proxies if p.country_code != "IR" and p.is_working],
        key=lambda p: p.latency or float("inf"),
    )[:5]

    for relay in relays_ir:
        for exit_node in foreign_exits:
            stats["attempted"] += 1
            chain_objs = create_chain(relay, exit_node, "INTRANET-BRIDGE")
            if chain_objs:
                chains["intranet"].extend(chain_objs)
                stats["succeeded"] += 1
            else:
                stats["failed"] += 1

    # --- CHAIN 2: THE IPv6 PORTAL ---
    for idx, exit_node in enumerate(exits_ipv6[:20]):  # Limit to avoid bloat
        if relays_dual_stack:
            stats["attempted"] += 1
            try:
                # Deterministic selection based on exit node ID
                relay = _deterministic_select(relays_dual_stack, f"ipv6-{exit_node.id}")
                chain_objs = create_chain(relay, exit_node, "IPv6-GATEWAY")
                if chain_objs:
                    chains["ipv6"].extend(chain_objs)
                    stats["succeeded"] += 1
                else:
                    stats["failed"] += 1
            except ValueError as e:
                logger.warning(f"IPv6 chain {idx} selection failed: {e}")
                stats["failed"] += 1

    # --- CHAIN 3: THE STREAMER ---
    for idx, exit_node in enumerate(exits_streaming[:20]):
        if relays_fast:
            stats["attempted"] += 1
            try:
                # Deterministic selection based on exit node ID
                relay = _deterministic_select(relays_fast, f"stream-{exit_node.id}")
                chain_objs = create_chain(relay, exit_node, "STREAMING-ACCEL")
                if chain_objs:
                    chains["streamer"].extend(chain_objs)
                    stats["succeeded"] += 1
                else:
                    stats["failed"] += 1
            except ValueError as e:
                logger.warning(f"Streaming chain {idx} selection failed: {e}")
                stats["failed"] += 1

    # --- CHAIN 4: EXPERIMENTAL - FIXED with guards ---
    if (
        relays_fast
        and exits_standard
        and len(relays_fast) > 0
        and len(exits_standard) > 0
    ):
        for i in range(min(10, len(relays_fast), len(exits_standard))):
            stats["attempted"] += 1
            try:
                relay = _deterministic_select(relays_fast, f"exp-relay-{i}")
                exit_node = _deterministic_select(exits_standard, f"exp-exit-{i}")
                chain_objs = create_chain(relay, exit_node, f"EXP-{i}")
                if chain_objs:
                    chains["experimental"].extend(chain_objs)
                    stats["succeeded"] += 1
                else:
                    stats["failed"] += 1
            except ValueError as e:
                logger.warning(f"Experimental chain {i} selection failed: {e}")
                stats["failed"] += 1

    # Log statistics
    chain_counts = {
        k: len(v) // 2 for k, v in chains.items()
    }  # Each chain has 2 outbounds
    total_chains = sum(chain_counts.values())

    if total_chains > 0:
        logger.info(
            f"Smart chains generated: {stats['succeeded']}/{stats['attempted']} "
            f"({stats['failed']} failures). "
            f"intranet={chain_counts['intranet']}, ipv6={chain_counts['ipv6']}, "
            f"streamer={chain_counts['streamer']}, experimental={chain_counts['experimental']}"
        )
    else:
        logger.warning("No smart chains generated - check relay/exit availability")

    return chains
