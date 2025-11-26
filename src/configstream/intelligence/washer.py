"""
Proxy Washing and Chaining Intelligence.
Handles the logic for creating proxy chains and washing proxies through WARP/WireGuard.
"""

import json
import hashlib
import random
import logging
import threading
import httpx
from typing import List, Dict, Optional, Set, Any, Tuple
from ..models import Proxy
from ..converters import to_singbox_outbound

logger = logging.getLogger(__name__)

# Static fallback if fetch fails
DEFAULT_CLEAN_IPS = ["162.159.192.1", "162.159.193.10", "162.159.195.5"]
CLEAN_IP_SOURCE = "https://raw.githubusercontent.com/ircfspace/warpendpoint/main/export/singbox/singbox.json"


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
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse warp_keys_json: {e}")
            self.warp_keys = []
        self.seen_chains: Set[str] = set()
        self._seen_chains_lock = threading.Lock()
        self.clean_ips: List[str] = []

    async def fetch_clean_ips(self):
        """Fetches the latest clean IPs for WARP endpoints."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Better source for raw IPs:
                # https://raw.githubusercontent.com/ircfspace/endpoint/main/ipv4.txt
                resp = await client.get(
                    "https://raw.githubusercontent.com/ircfspace/endpoint/main/ipv4.txt"
                )
                if resp.status_code == 200:
                    # Filter valid IPs
                    lines = [
                        line.strip() for line in resp.text.splitlines() if line.strip()
                    ]
                    # Basic validation (check if it looks like an IP)
                    self.clean_ips = [ip for ip in lines if ip.count(".") == 3]
                    logger.info(
                        "Fetched %d clean IPs for Washing.", len(self.clean_ips)
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch clean IPs: {e}. Using defaults.")
            self.clean_ips = []

    def _get_clean_endpoint(self, relay_id: str) -> str:
        """Deterministically selects a clean IP based on proxy ID."""
        pool = self.clean_ips if self.clean_ips else DEFAULT_CLEAN_IPS
        # Consistent hashing so the same proxy always gets the same endpoint (stability)
        hash_val = int(hashlib.md5(relay_id.encode()).hexdigest(), 16)
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
        hash_val = int(hashlib.md5(relay_id.encode()).hexdigest(), 16)
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
        washed_outbounds = []
        washed_ids = set()

        # 1. Identify Candidates
        # Current strategy: when WARP keys are available, wash ALL working
        # proxies rather than relying solely on tags. Tags are still useful
        # for downstream labeling but not a hard requirement here.
        candidates = [p for p in proxies if p.is_working and self.warp_keys]

        for i, relay in enumerate(candidates):
            # 2. Select the "Soap" (Exit Node)
            exit_key = self._get_consistent_exit(relay.id, self.warp_keys)
            if not exit_key or "private_key" not in exit_key:
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
                self.seen_chains.add(chain_id)

            # 4. Construct the Chain Objects
            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                continue

            relay_tag = f"RELAY-{chain_id}"
            relay_out["tag"] = relay_tag

            # --- NEW: Use Clean IP ---
            clean_endpoint = self._get_clean_endpoint(relay.id)
            clean_port = 2408  # Standard WireGuard port

            exit_tag = f"🛡️ Secure-{relay.country_code}-{i+1}"
            warp_out = {
                "type": "wireguard",
                "tag": exit_tag,
                "local_address": ["172.16.0.2/32"],
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

    # --- CHAIN 1: THE INTRANET BRIDGE (Gold Standard) ---
    for relay in relays_ir:
        # Link to top 5 fastest foreign exits
        for exit_node in proxies[:5]:
            if exit_node.country_code != "IR" and exit_node.is_working:
                chain_objs = create_chain(relay, exit_node, "INTRANET-BRIDGE")
                if chain_objs:
                    chains["intranet"].extend(chain_objs)

    # --- CHAIN 2: THE IPv6 PORTAL ---
    for exit_node in exits_ipv6[:20]:  # Limit to avoid bloat
        if relays_dual_stack:
            relay = random.choice(relays_dual_stack)
            chain_objs = create_chain(relay, exit_node, "IPv6-GATEWAY")
            if chain_objs:
                chains["ipv6"].extend(chain_objs)

    # --- CHAIN 3: THE STREAMER ---
    for exit_node in exits_streaming[:20]:
        if relays_fast:
            relay = random.choice(relays_fast)
            chain_objs = create_chain(relay, exit_node, "STREAMING-ACCEL")
            if chain_objs:
                chains["streamer"].extend(chain_objs)

    # --- CHAIN 4: EXPERIMENTAL (Hysteria -> VMess) ---
    if relays_fast and exits_standard:
        for i in range(10):
            relay = random.choice(relays_fast)
            exit_node = random.choice(exits_standard)
            chain_objs = create_chain(relay, exit_node, f"EXP-{i}")
            if chain_objs:
                chains["experimental"].extend(chain_objs)

    return chains
