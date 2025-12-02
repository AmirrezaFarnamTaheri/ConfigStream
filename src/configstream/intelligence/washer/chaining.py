import hashlib
import logging
from typing import List, Dict, Any

from ...models import Proxy
from ...converters import to_singbox_outbound

logger = logging.getLogger(__name__)

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
