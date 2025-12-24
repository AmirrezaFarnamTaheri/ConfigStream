from typing import List, Dict, Any, Optional, Tuple
import logging
import ipaddress
import hashlib
import math

from ..converters import to_singbox_outbound
from ..models import Proxy

logger = logging.getLogger(__name__)

# --- Geodesic Logic ---
try:
    from geopy.distance import geodesic  # type: ignore

    GEOPY_AVAILABLE = True
except ImportError:
    logger.warning(
        "geopy not installed - optimal relay selection disabled. Install with: pip install geopy"
    )
    GEOPY_AVAILABLE = False

    # Fallback haversine distance calculation
    # Define a stub class to mimic geopy's Distance object
    class DistanceStub:
        def __init__(self, km: float):
            self.km = km

    def geodesic(
        coord1: Tuple[float, float], coord2: Tuple[float, float]
    ) -> DistanceStub:
        """Fallback distance calculation using haversine formula."""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        R = 6371  # Earth radius in km

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return DistanceStub(R * c)


# Minimal Proxy definition for typing
class ProxyStub:
    def __init__(self, country: str, lat: float, lon: float, protocol: str):
        self.country = country
        self.lat = lat
        self.lon = lon
        self.protocol = protocol


# Expanded list of country coordinates (approximate center lat/lon)
COUNTRIES: Dict[str, Tuple[float, float]] = {
    # Censored Origins
    "IR": (32.4279, 53.6880),  # Iran
    "CN": (35.8617, 104.1954),  # China
    "RU": (61.5240, 105.3188),  # Russia
    "TM": (38.9697, 59.5563),  # Turkmenistan
    "CU": (21.5218, -77.7812),  # Cuba
    "VE": (6.4238, -66.5897),  # Venezuela
    "SA": (23.8859, 45.0792),  # Saudi Arabia
    # Strategic Relays (Neighbors / Low Latency)
    "TR": (38.9637, 35.2433),  # Turkey (Gateway to EU for IR)
    "AE": (23.4241, 53.8478),  # UAE (Hub for Middle East)
    "IQ": (33.2232, 43.6793),  # Iraq
    "AM": (40.0691, 45.0382),  # Armenia
    "AZ": (40.1431, 47.5769),  # Azerbaijan
    "HK": (22.3193, 114.1694),  # Hong Kong (Gateway for CN)
    "SG": (1.3521, 103.8198),  # Singapore (SE Asia Hub)
    "JP": (36.2048, 138.2529),  # Japan
    "KR": (35.9078, 127.7669),  # South Korea
    "TW": (23.6978, 120.9605),  # Taiwan
    "KZ": (48.0196, 66.9237),  # Kazakhstan (Hub for Central Asia)
    # Major Exit Nodes (Western Hubs)
    "US": (37.0902, -95.7129),  # USA
    "DE": (51.1657, 10.4515),  # Germany
    "NL": (52.1326, 5.2913),  # Netherlands
    "GB": (55.3781, -3.4360),  # United Kingdom
    "FR": (46.2276, 2.2137),  # France
    "CA": (56.1304, -106.3468),  # Canada
    "AU": (-25.2744, 133.7751),  # Australia
    "SE": (60.1282, 18.6435),  # Sweden
    "FI": (61.9241, 25.7482),  # Finland
    "PL": (51.9194, 19.1451),  # Poland
    "IT": (41.8719, 12.5674),  # Italy
    "CH": (46.8182, 8.2275),  # Switzerland
    "UA": (48.3794, 31.1656),  # Ukraine
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Wrapper for geodesic, returning km"""
    dist_obj = geodesic((lat1, lon1), (lat2, lon2))
    # Ensure we extract float km value safely
    if hasattr(dist_obj, "km"):
        return float(dist_obj.km)
    return float(
        dist_obj
    )  # Fallback if library returns raw float (unlikely for geopy but good for mocks)


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
        # [FIX] Inject metadata for process tracking
        warp_out["_process"] = "chain"

        chain.append(warp_out)
    else:
        # [FIX] Inject metadata for standard chains (no warp)
        # We attach it to the exit node's config as it's the final hop
        exit_out["_process"] = "chain"

    return chain


def _deterministic_select(pool: List[Proxy], seed: str) -> Optional[Proxy]:
    """Selects a proxy from a pool deterministically based on a seed string."""
    if not pool:
        return None
    hash_val = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return pool[hash_val % len(pool)]


def find_optimal_relay(
    origin_cc: str, exit_node: ProxyStub, candidates: List[ProxyStub]
) -> Dict[str, Any]:
    """
    Finds the best relay node between origin and exit node using geodesic distance.
    Returns the best relay proxy and metadata.
    """
    if origin_cc not in COUNTRIES:
        # If origin not in DB, we can't optimize, return error
        return {"error": f"Unknown origin country: {origin_cc}"}

    origin_coords = COUNTRIES[origin_cc]
    exit_coords = (exit_node.lat, exit_node.lon)

    best_relay: Optional[ProxyStub] = None
    min_score = float("inf")

    # Direct distance for comparison
    direct_dist = haversine(
        origin_coords[0], origin_coords[1], exit_coords[0], exit_coords[1]
    )

    for relay in candidates:
        if relay.country == origin_cc or relay.country == exit_node.country:
            continue

        relay_coords = (relay.lat, relay.lon)

        # Calculate total path length
        d1 = haversine(
            origin_coords[0], origin_coords[1], relay_coords[0], relay_coords[1]
        )
        d2 = haversine(relay_coords[0], relay_coords[1], exit_coords[0], exit_coords[1])
        total_path = d1 + d2

        # Heuristic: Protocol penalty (prefer stealthier protocols for Relay)
        penalty = 0
        if relay.protocol not in ["hysteria2", "vless", "tuic"]:
            penalty = 500  # Add equivalent of 500km penalty

        # Optimization: Triangle Inequality Check
        # If path is > 1.5x direct path, it's too inefficient
        if total_path > 1.5 * direct_dist:
            penalty += 1000

        score = total_path + penalty

        if score < min_score:
            min_score = score
            best_relay = relay

    if best_relay:
        return {
            "relay": best_relay,
            "exit": exit_node,
            "total_distance": min_score,
            "direct_distance": direct_dist,
        }
    else:
        return {"error": "No suitable relay found"}


def generate_smart_chains(
    proxies: List[Proxy],
    washer: Any = None,  # Using Any to avoid circular import issues with ProxyWasher
) -> Dict[str, List[List[Dict[str, Any]]]]:
    """
    Generates topology-aware proxy chains.
    Now supports an optional 'washer' to generate 3-hop washed chains.
    """
    # Fix: Return type hint to List[List[Dict]] (list of chains, where chain is list of outbounds)
    chains: Dict[str, List[List[Dict[str, Any]]]] = {
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
    streaming_countries = [
        "US",
        "DE",
        "GB",
        "NL",
        "FR",
        "JP",
        "SG",
        "CA",
        "AU",
        "SE",
        "CH",
    ]
    exits_streaming = [
        p for p in foreign_exits if p.country_code in streaming_countries
    ]

    # Standard protocols for exits (vmess, ss, trojan)
    exits_standard = [
        p for p in foreign_exits if p.protocol in ("vmess", "shadowsocks", "trojan")
    ]

    # --- CHAIN 1: THE INTRANET BRIDGE (Standard & Washed) ---
    # Strategy: User (Intranet) -> Relay (IR) -> Exit (Foreign) [-> WARP]

    # [OPTIMIZATION] Pre-calculate Foreign Exit Coordinates to avoid repetitive lookups
    # Only compute for exits in known countries
    optimized_exits: List[Tuple[Proxy, float, float]] = []
    for ep in foreign_exits:
        if ep.country_code in COUNTRIES:
            lat, lon = COUNTRIES[ep.country_code]
            optimized_exits.append((ep, lat, lon))

    for relay in relays_ir:
        # [FIX] Use geographical optimization to find the best exit for this relay
        # Pick the exit with minimum distance to the relay
        best_exit = None

        if relay.country_code in COUNTRIES:
            relay_lat, relay_lon = COUNTRIES[relay.country_code]

            # Use optimized list
            min_distance = float("inf")
            for exit_p, exit_lat, exit_lon in optimized_exits:
                dist = haversine(relay_lat, relay_lon, exit_lat, exit_lon)
                if dist < min_distance:
                    min_distance = dist
                    best_exit = exit_p

        # Fallback to deterministic if optimization fails or no coordinates
        exit_node = (
            best_exit
            if best_exit
            else _deterministic_select(foreign_exits, f"INTRANET-{relay.id}")
        )

        if exit_node is not None:
            # 1. Standard Chain (Fallback)
            chain_std = create_chain(relay, exit_node, "INTRANET")
            if chain_std:
                chains["intranet"].append(chain_std)

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
                        chains["intranet_washed"].append(chain_washed)

    # --- CHAIN 2: IPv6 PORTAL ---
    # Strategy: User (IPv4) -> Relay (Dual Stack) -> Exit (IPv6 Only)
    for exit_node in exits_ipv6:
        # Pick a robust dual-stack relay
        ipv6_relay = _deterministic_select(relays_dual_stack, f"IPV6-{exit_node.id}")
        if ipv6_relay is not None:
            chain = create_chain(ipv6_relay, exit_node, "IPv6-GATEWAY")
            if chain:
                chains["ipv6"].append(chain)

    # --- CHAIN 3: STREAMING ACCELERATOR ---
    # Strategy: User -> Relay (UDP Optimized) -> Exit (Streaming Region)
    for exit_node in exits_streaming:
        # Pick a fast relay
        stream_relay = _deterministic_select(relays_fast, f"STREAM-{exit_node.id}")
        if stream_relay is not None:
            chain = create_chain(stream_relay, exit_node, "STREAMING-ACCEL")
            if chain:
                chains["streamer"].append(chain)

    # --- CHAIN 4: EXPERIMENTAL (Protocol Wrapping) ---
    # Strategy: Wrap standard protocols in Hysteria/TUIC
    for exit_node in exits_standard:
        exp_relay = _deterministic_select(relays_fast, f"EXP-{exit_node.id}")
        if exp_relay is not None:
            chain = create_chain(exp_relay, exit_node, "EXP-WRAP")
            if chain:
                chains["experimental"].append(chain)

    total_chains = sum(len(v) for v in chains.values())

    logger.info(
        f"Smart chains generated: {total_chains} chains across {len(chains)} categories. "
        f"intranet={len(chains['intranet'])}, intranet_washed={len(chains['intranet_washed'])}, "
        f"ipv6={len(chains['ipv6'])}, streamer={len(chains['streamer'])}"
    )

    return chains
