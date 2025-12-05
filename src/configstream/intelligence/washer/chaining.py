import ipaddress
import hashlib
import logging
from typing import List, Dict, Any, Optional

from ...models import Proxy
from ...converters import to_singbox_outbound
from ...quality.geo import COUNTRIES, haversine

logger = logging.getLogger(__name__)

# Import Optional and ProxyWasher (if type checking needed, use string forward ref)
# from .core import ProxyWasher


class ProxyStub:
    """Minimal proxy representation for geodesic calculations."""

    def __init__(self, country: str, lat: float, lon: float, protocol: str):
        self.country = country
        self.lat = lat
        self.lon = lon
        self.protocol = protocol


def is_likely_ipv4(address: str) -> bool:
    """
    Returns True if address is IPv4 literal or a Domain (assumed dual-stack).
    Returns False ONLY if it is explicitly an IPv6 literal.
    """
    try:
        # If it parses as IPv6, it's definitely NOT IPv4-safe
        ip = ipaddress.ip_address(address)
        return isinstance(ip, ipaddress.IPv4Address)
    except ValueError:
        # It's a domain name. Most domains support IPv4, so we assume Safe.
        return True


def create_chain(
    relay: Proxy,
    exit_node: Proxy,
    tag_prefix: str,
    warp_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:

    # 1. Standard Relay -> Exit construction (Existing Code)
    relay_out = to_singbox_outbound(relay)
    exit_out = to_singbox_outbound(exit_node)

    if not relay_out or not exit_out:
        return []

    relay_tag = f"{tag_prefix}-RELAY-{relay.id[:6]}"
    # If washing, mark the Exit as 'Middle' to avoid confusion, or keep standard naming
    exit_tag_suffix = "EXIT" if not warp_config else "MID"
    exit_tag = f"{tag_prefix}-{exit_tag_suffix}-{exit_node.country}-{exit_node.id[:6]}"

    relay_out["tag"] = relay_tag
    exit_out["tag"] = exit_tag
    exit_out["detour"] = relay_tag

    chain = [relay_out, exit_out]

    # 2. Add WARP Hop (The New Logic)
    if warp_config:
        warp_tag = f"{tag_prefix}-WARP-FINAL-{exit_node.id[:4]}"

        # Create the WireGuard object using the config from Washer
        warp_out = warp_config.copy()
        warp_out["tag"] = warp_tag
        warp_out["detour"] = exit_tag  # The magic: WARP goes through Exit

        chain.append(warp_out)

    return chain


def _deterministic_select(pool: List[Proxy], seed: str) -> Optional[Proxy]:
    """Selects a proxy from a pool deterministically based on a seed string."""
    if not pool:
        return None
    hash_val = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return pool[hash_val % len(pool)]


def find_optimal_relay(
    origin_country: str, target: ProxyStub, relays: List[ProxyStub]
) -> Dict[str, Any]:
    """
    Finds the relay that minimizes the total geodesic distance:
    Origin -> Relay -> Target
    """
    if origin_country not in COUNTRIES:
        return {"error": "Origin country unknown"}

    origin_lat, origin_lon = COUNTRIES[origin_country]
    best_relay = None
    min_distance = float("inf")

    for relay in relays:
        # Penalty for cross-continental hops if needed, or protocol preference
        d1 = haversine(origin_lat, origin_lon, relay.lat, relay.lon)
        d2 = haversine(relay.lat, relay.lon, target.lat, target.lon)
        total_dist = d1 + d2

        if total_dist < min_distance:
            min_distance = total_dist
            best_relay = relay

    # ensure best_relay is not None before returning or handle in type hint
    # For now, it might be None if list is empty
    return {
        "relay": best_relay,
        "total_distance": min_distance,
        "origin": origin_country,
    }


def generate_smart_chains(
    proxies: List[Proxy],
    washer: Any = None,  # Using Any to avoid circular import issues with ProxyWasher
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generates topology-aware proxy chains.
    Now supports an optional 'washer' to generate 3-hop washed chains.
    """
    chains: Dict[str, List[Dict[str, Any]]] = {
        "intranet": [],
        "intranet_washed": [],  # <--- New Category
        "ipv6": [],
        "streamer": [],
        "experimental": [],
    }

    # 1. Categorize Proxies
    # Relays: Must be in specific regions or have specific capabilities
    # 'IR' is the standard "Intranet" origin for this project logic
    relays_ir = [p for p in proxies if p.country_code == "IR" and p.is_working]

    # Fast protocols (Hysteria2, TUIC) are good relays for streaming
    relays_fast = [
        p for p in proxies if p.is_working and p.protocol in ("hysteria2", "tuic")
    ]

    # Dual-stack relays (IPv4 access) needed to reach IPv6 exits
    # UPDATED: Robust IPv4 check
    relays_dual_stack = [
        p for p in proxies if p.is_working and is_likely_ipv4(p.address)
    ]

    # Exits: Destination specific
    # Foreign Exits (Not IR)
    foreign_exits = [p for p in proxies if p.country_code != "IR" and p.is_working]

    # IPv6 Only Exits (heuristic: ':' in address) - strictly IPv6 literals often implies IPv6-only host
    exits_ipv6 = [
        p
        for p in proxies
        if p.is_working and ":" in p.address and not is_likely_ipv4(p.address)
    ]

    # Streaming friendly locations
    streaming_countries = ["US", "DE", "GB", "NL", "FR", "JP"]
    exits_streaming = [
        p for p in foreign_exits if p.country_code in streaming_countries
    ]

    # Standard protocols for exits (vmess, ss, trojan)
    exits_standard = [
        p for p in foreign_exits if p.protocol in ("vmess", "shadowsocks", "trojan")
    ]

    # --- CHAIN 1: THE INTRANET BRIDGE (Standard & Washed) ---
    # Strategy: User (Intranet) -> Relay (IR) -> Exit (Foreign) [-> WARP]
    # To avoid explosion (N*M), we select 1 deterministic exit per relay
    for relay in relays_ir:
        # Deterministically pick one exit for this relay
        exit_node = _deterministic_select(foreign_exits, f"INTRANET-{relay.id}")

        if exit_node is not None:
            # 1. Standard Chain (Fallback)
            chain_std = create_chain(relay, exit_node, "INTRANET")
            if chain_std:
                chains["intranet"].extend(chain_std)

            # 2. Washed Chain (Premium) - Only if washer is available
            if washer:
                # Generate a unique seed for this specific path
                seed = f"{relay.id}-{exit_node.id}"
                warp_cfg = washer.get_warp_config(seed)

                if warp_cfg:
                    # Create chain with WARP appended
                    chain_washed = create_chain(
                        relay, exit_node, "INTRANET-SECURE", warp_config=warp_cfg
                    )
                    if chain_washed:
                        chains["intranet_washed"].extend(chain_washed)

    # --- CHAIN 2: IPv6 PORTAL ---
    # Strategy: User (IPv4) -> Relay (Dual Stack) -> Exit (IPv6 Only)
    for exit_node in exits_ipv6:
        # Pick a robust dual-stack relay
        ipv6_relay = _deterministic_select(relays_dual_stack, f"IPV6-{exit_node.id}")
        if ipv6_relay is not None:
            chain = create_chain(ipv6_relay, exit_node, "IPv6-GATEWAY")
            if chain:
                chains["ipv6"].extend(chain)

    # --- CHAIN 3: STREAMING ACCELERATOR ---
    # Strategy: User -> Relay (UDP Optimized) -> Exit (Streaming Region)
    for exit_node in exits_streaming:
        # Pick a fast relay
        stream_relay = _deterministic_select(relays_fast, f"STREAM-{exit_node.id}")
        if stream_relay is not None:
            chain = create_chain(stream_relay, exit_node, "STREAMING-ACCEL")
            if chain:
                chains["streamer"].extend(chain)

    # --- CHAIN 4: EXPERIMENTAL (Protocol Wrapping) ---
    # Strategy: Wrap standard protocols in Hysteria/TUIC
    for exit_node in exits_standard:
        exp_relay = _deterministic_select(relays_fast, f"EXP-{exit_node.id}")
        if exp_relay is not None:
            chain = create_chain(exp_relay, exit_node, "EXP-WRAP")
            if chain:
                chains["experimental"].extend(chain)

    total_chains = sum(len(v) for v in chains.values())
    # Adjust count because each chain is a list of objects (2 or 3), so divide by average length ~2.1
    # Actually create_chain returns a list of outbound dicts.
    # The 'chains' dict values are flat lists of outbounds.
    # So we just count outbounds.

    logger.info(
        f"Smart chains generated: {total_chains} outbound objects across {len(chains)} categories. "
        f"intranet={len(chains['intranet'])}, intranet_washed={len(chains['intranet_washed'])}, "
        f"ipv6={len(chains['ipv6'])}, streamer={len(chains['streamer'])}"
    )

    return chains
