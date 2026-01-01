# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import List, Dict, Any, Optional, Tuple
import logging
import ipaddress
import hashlib
import math

from configstream.converters import to_singbox_outbound
from configstream.models import Proxy

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


# Comprehensive country coordinates database (approximate center lat/lon)
# Enhanced with 80+ countries for global coverage
COUNTRIES: Dict[str, Tuple[float, float]] = {
    # === Censored Origins ===
    "IR": (32.4279, 53.6880),  # Iran
    "CN": (35.8617, 104.1954),  # China
    "RU": (61.5240, 105.3188),  # Russia
    "TM": (38.9697, 59.5563),  # Turkmenistan
    "CU": (21.5218, -77.7812),  # Cuba
    "VE": (6.4238, -66.5897),  # Venezuela
    "SA": (23.8859, 45.0792),  # Saudi Arabia
    "BY": (53.7098, 27.9534),  # Belarus
    "SY": (34.8021, 38.9968),  # Syria
    "KP": (40.3399, 127.5101),  # North Korea
    # === Strategic Relays (Middle East & Central Asia) ===
    "TR": (38.9637, 35.2433),  # Turkey (Gateway to EU for IR)
    "AE": (23.4241, 53.8478),  # UAE (Hub for Middle East)
    "IQ": (33.2232, 43.6793),  # Iraq
    "AM": (40.0691, 45.0382),  # Armenia
    "AZ": (40.1431, 47.5769),  # Azerbaijan
    "GE": (42.3154, 43.3569),  # Georgia
    "KZ": (48.0196, 66.9237),  # Kazakhstan (Hub for Central Asia)
    "UZ": (41.3775, 64.5853),  # Uzbekistan
    "KG": (41.2044, 74.7661),  # Kyrgyzstan
    "TJ": (38.8610, 71.2761),  # Tajikistan
    "AF": (33.9391, 67.7100),  # Afghanistan
    "PK": (30.3753, 69.3451),  # Pakistan
    "QA": (25.3548, 51.1839),  # Qatar
    "OM": (21.4735, 55.9754),  # Oman
    "BH": (26.0667, 50.5577),  # Bahrain
    "KW": (29.3117, 47.4818),  # Kuwait
    "JO": (30.5852, 36.2384),  # Jordan
    "LB": (33.8547, 35.8623),  # Lebanon
    "IL": (31.0461, 34.8516),  # Israel
    # === Asia-Pacific Hubs ===
    "HK": (22.3193, 114.1694),  # Hong Kong (Gateway for CN)
    "SG": (1.3521, 103.8198),  # Singapore (SE Asia Hub)
    "JP": (36.2048, 138.2529),  # Japan
    "KR": (35.9078, 127.7669),  # South Korea
    "TW": (23.6978, 120.9605),  # Taiwan
    "MY": (4.2105, 101.9758),  # Malaysia
    "TH": (15.8700, 100.9925),  # Thailand
    "VN": (14.0583, 108.2772),  # Vietnam
    "ID": (-0.7893, 113.9213),  # Indonesia
    "PH": (12.8797, 121.7740),  # Philippines
    "IN": (20.5937, 78.9629),  # India
    "BD": (23.6850, 90.3563),  # Bangladesh
    "LK": (7.8731, 80.7718),  # Sri Lanka
    "NP": (28.3949, 84.1240),  # Nepal
    "MM": (21.9162, 95.9560),  # Myanmar
    "KH": (12.5657, 104.9910),  # Cambodia
    "LA": (19.8563, 102.4955),  # Laos
    "MN": (46.8625, 103.8467),  # Mongolia
    # === Western Europe (Premium Exits) ===
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
    "ES": (40.4637, -3.7492),  # Spain
    "PT": (39.3999, -8.2245),  # Portugal
    "NO": (60.4720, 8.4689),  # Norway
    "DK": (56.2639, 9.5018),  # Denmark
    "IE": (53.4129, -8.2439),  # Ireland
    "AT": (47.5162, 14.5501),  # Austria
    "BE": (50.5039, 4.4699),  # Belgium
    "CZ": (49.8175, 15.4730),  # Czech Republic
    "RO": (45.9432, 24.9668),  # Romania
    "GR": (39.0742, 21.8243),  # Greece
    "BG": (42.7339, 25.4858),  # Bulgaria
    "HR": (45.1000, 15.2000),  # Croatia
    "RS": (44.0165, 21.0059),  # Serbia
    "SK": (48.6690, 19.6990),  # Slovakia
    "SI": (46.1512, 14.9955),  # Slovenia
    "HU": (47.1625, 19.5033),  # Hungary
    "LT": (55.1694, 23.8813),  # Lithuania
    "LV": (56.8796, 24.6032),  # Latvia
    "EE": (58.5953, 25.0136),  # Estonia
    "IS": (64.9631, -19.0208),  # Iceland
    # === Americas ===
    "MX": (23.6345, -102.5528),  # Mexico
    "BR": (-14.2350, -51.9253),  # Brazil
    "AR": (-38.4161, -63.6167),  # Argentina
    "CL": (-35.6751, -71.5430),  # Chile
    "CO": (4.5709, -74.2973),  # Colombia
    "PE": (-9.1900, -75.0152),  # Peru
    "EC": (-1.8312, -78.1834),  # Ecuador
    "CR": (9.7489, -83.7534),  # Costa Rica
    "PA": (8.5380, -80.7821),  # Panama
    # === Africa ===
    "ZA": (-30.5595, 22.9375),  # South Africa
    "EG": (26.8206, 28.2887),  # Egypt
    "NG": (9.0820, 8.6753),  # Nigeria
    "KE": (-0.0236, 37.9062),  # Kenya
    "MA": (31.7917, -7.0926),  # Morocco
    "TN": (33.8869, 9.5375),  # Tunisia
    "DZ": (28.0339, 1.6596),  # Algeria
    "GH": (7.9465, -1.0232),  # Ghana
    "ET": (9.1450, 40.4897),  # Ethiopia
    "UG": (1.3733, 32.2903),  # Uganda
    # === Oceania ===
    "NZ": (-40.9006, 174.8860),  # New Zealand
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


# Protocol Intelligence: Strategic scoring for different use cases
PROTOCOL_SCORES = {
    # Stealth Protocols (Good for censorship resistance)
    "vless": {"stealth": 10, "speed": 7, "reliability": 8, "penalty_km": 0},
    "trojan": {"stealth": 9, "speed": 7, "reliability": 9, "penalty_km": 100},
    "vmess": {"stealth": 8, "speed": 6, "reliability": 8, "penalty_km": 200},
    # Speed Protocols (Good for streaming/low latency)
    "hysteria2": {"stealth": 6, "speed": 10, "reliability": 7, "penalty_km": 0},
    "tuic": {"stealth": 6, "speed": 9, "reliability": 7, "penalty_km": 50},
    "hysteria": {"stealth": 5, "speed": 9, "reliability": 6, "penalty_km": 100},
    # Standard Protocols
    "shadowsocks": {"stealth": 7, "speed": 8, "reliability": 9, "penalty_km": 200},
    "wireguard": {"stealth": 4, "speed": 10, "reliability": 10, "penalty_km": 300},
    "ssh": {"stealth": 9, "speed": 5, "reliability": 10, "penalty_km": 400},
    # Legacy
    "http": {"stealth": 3, "speed": 4, "reliability": 6, "penalty_km": 600},
    "socks": {"stealth": 2, "speed": 5, "reliability": 7, "penalty_km": 600},
}

# Censorship severity by country (higher = more censored)
CENSORSHIP_LEVELS = {
    "CN": 10,
    "IR": 10,
    "TM": 9,
    "KP": 10,
    "CU": 8,
    "SY": 9,
    "BY": 7,
    "RU": 7,
    "VE": 6,
    "SA": 6,
    "TR": 5,
    "EG": 5,
    "TH": 4,
    "VN": 4,
    "PK": 5,
}


def calculate_relay_score(
    relay: ProxyStub,
    origin_cc: str,
    exit_node: ProxyStub,
    origin_coords: Tuple[float, float],
    exit_coords: Tuple[float, float],
    direct_dist: float,
    optimization_mode: str = "balanced",
) -> float:
    """
    Multi-criteria scoring for relay selection.

    Args:
        relay: Candidate relay proxy
        origin_cc: Origin country code
        exit_node: Destination exit node
        origin_coords: Origin coordinates (lat, lon)
        exit_coords: Exit coordinates (lat, lon)
        direct_dist: Direct distance from origin to exit
        optimization_mode: 'stealth', 'speed', 'balanced', or 'reliability'

    Returns:
        Score (lower is better)
    """
    if relay.country == origin_cc or relay.country == exit_node.country:
        return float("inf")

    relay_coords = (relay.lat, relay.lon)

    # Geographic distance component
    d1 = haversine(origin_coords[0], origin_coords[1], relay_coords[0], relay_coords[1])
    d2 = haversine(relay_coords[0], relay_coords[1], exit_coords[0], exit_coords[1])
    total_path = d1 + d2

    # Get protocol characteristics
    protocol_data = PROTOCOL_SCORES.get(
        relay.protocol, {"stealth": 5, "speed": 5, "reliability": 5, "penalty_km": 500}
    )

    # Base distance penalty
    distance_score = total_path + protocol_data["penalty_km"]

    # Triangle inequality penalty (route efficiency)
    if total_path > 1.8 * direct_dist:
        distance_score += 2000  # Very inefficient route
    elif total_path > 1.5 * direct_dist:
        distance_score += 1000  # Moderately inefficient

    # Mode-specific optimization
    mode_penalty = 0
    if optimization_mode == "stealth":
        # Prefer high-stealth protocols
        stealth_score = protocol_data["stealth"]
        mode_penalty = (10 - stealth_score) * 200  # Lower stealth = higher penalty
    elif optimization_mode == "speed":
        # Prefer high-speed protocols
        speed_score = protocol_data["speed"]
        mode_penalty = (10 - speed_score) * 150
    elif optimization_mode == "reliability":
        # Prefer reliable protocols
        reliability_score = protocol_data["reliability"]
        mode_penalty = (10 - reliability_score) * 100
    else:  # balanced
        # Balanced scoring
        avg_score = (
            protocol_data["stealth"]
            + protocol_data["speed"]
            + protocol_data["reliability"]
        ) / 3
        mode_penalty = int((10 - avg_score) * 100)

    # Censorship-aware bonus
    origin_censorship = CENSORSHIP_LEVELS.get(origin_cc, 0)
    relay_censorship = CENSORSHIP_LEVELS.get(relay.country, 0)

    # If origin is heavily censored, prefer relays in less censored countries
    if origin_censorship >= 7 and relay_censorship <= 3:
        distance_score -= 300  # Bonus for transitioning to free region

    # If relay is in neighboring country with similar censorship, add penalty
    if abs(origin_censorship - relay_censorship) <= 2 and d1 < 500:
        mode_penalty += 200

    return distance_score + mode_penalty


def find_optimal_relay(
    origin_cc: str,
    exit_node: ProxyStub,
    candidates: List[ProxyStub],
    optimization_mode: str = "balanced",
) -> Dict[str, Any]:
    """
    Enhanced relay selection with multi-criteria scoring.

    Args:
        origin_cc: Origin country code
        exit_node: Destination exit node
        candidates: List of candidate relay proxies
        optimization_mode: 'stealth', 'speed', 'balanced', or 'reliability'

    Returns:
        Dict with best relay and metadata, or error message
    """
    if origin_cc not in COUNTRIES:
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
        score = calculate_relay_score(
            relay,
            origin_cc,
            exit_node,
            origin_coords,
            exit_coords,
            direct_dist,
            optimization_mode,
        )

        if score < min_score:
            min_score = score
            best_relay = relay

    if best_relay:
        return {
            "relay": best_relay,
            "exit": exit_node,
            "total_distance": min_score,
            "direct_distance": direct_dist,
            "optimization_mode": optimization_mode,
        }
    else:
        return {"error": "No suitable relay found"}


def generate_smart_chains(
    proxies: List[Proxy],
    washer: Any = None,  # Using Any to avoid circular import issues with ProxyWasher
) -> Dict[str, List[List[Dict[str, Any]]]]:
    """
    Enhanced smart chain generation with advanced routing intelligence.

    Generates topology-aware proxy chains with multiple optimization strategies:
    - Standard chains: 2-hop relay patterns
    - Washed chains: 3-hop with WARP tunnel
    - Censorship-resistant: Multi-hop stealth routes
    - Low-latency: Speed-optimized paths
    - High-anonymity: Maximum privacy routes
    - Load-balanced: Distributed traffic patterns

    Args:
        proxies: List of available proxy nodes
        washer: Optional ProxyWasher instance for WARP integration

    Returns:
        Dict mapping chain categories to lists of outbound configurations
    """
    # Enhanced chain categories
    chains: Dict[str, List[List[Dict[str, Any]]]] = {
        "intranet": [],  # Basic IR → Foreign
        "intranet_washed": [],  # IR → Foreign → WARP
        "ipv6": [],  # Dual-stack → IPv6
        "streamer": [],  # Speed-optimized for streaming
        "experimental": [],  # Protocol wrapping experiments
        "censorship_resistant": [],  # Multi-hop stealth chains
        "low_latency": [],  # Speed-first optimization
        "high_anonymity": [],  # Privacy-first (3+ hops)
        "load_balanced": [],  # Alternative routes for same destination
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

    # [FIX] Configurable intranet origin, defaulting to IR
    import os

    intranet_origin = os.getenv("INTRANET_ORIGIN", "IR")
    relays_intranet = [
        p for p in proxies if p.country_code == intranet_origin and p.is_working
    ]

    # [OPTIMIZATION] Pre-calculate Foreign Exit Coordinates to avoid repetitive lookups
    # Only compute for exits in known countries
    optimized_exits: List[Tuple[Proxy, float, float]] = []
    for ep in foreign_exits:
        if ep.country_code in COUNTRIES:
            lat, lon = COUNTRIES[ep.country_code]
            optimized_exits.append((ep, lat, lon))

    for relay in relays_intranet:
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

    # --- CHAIN 5: CENSORSHIP RESISTANT (Multi-hop Stealth) ---
    # Strategy: High-censorship origin → Stealth relay → Low-censorship relay → Exit
    # Uses vless/trojan protocols for maximum stealth
    censored_origins = [
        p
        for p in proxies
        if p.is_working and CENSORSHIP_LEVELS.get(p.country_code, 0) >= 7
    ]
    stealth_relays = [
        p
        for p in proxies
        if p.is_working and p.protocol in ("vless", "trojan", "vmess")
    ]
    free_relays = [
        p
        for p in proxies
        if p.is_working and CENSORSHIP_LEVELS.get(p.country_code, 0) <= 3
    ]

    for origin in censored_origins[:10]:  # Limit to avoid explosion
        # First hop: Origin → Nearby stealth relay
        nearby_stealth = [
            r
            for r in stealth_relays
            if r.country_code != origin.country_code
            and r.country_code in COUNTRIES
            and origin.country_code in COUNTRIES
        ]
        if not nearby_stealth:
            continue

        # Pick closest stealth relay
        origin_coords = COUNTRIES.get(origin.country_code)
        if not origin_coords:
            continue

        # [OPTIMIZATION] Sort nearby stealth relays by approximate distance first
        # This acts as a heuristic to limit the detailed check to top 50 candidates
        def heuristic_dist(r):
            rc = COUNTRIES.get(r.country_code)
            if not rc:
                return 99999
            return abs(rc[0] - origin_coords[0]) + abs(rc[1] - origin_coords[1])

        nearby_stealth.sort(key=heuristic_dist)

        best_stealth = None
        min_dist = float("inf")
        # Check only top 50 candidates to scale with large lists
        for relay in nearby_stealth[:50]:
            relay_coords = COUNTRIES.get(relay.country_code)
            if relay_coords:
                dist = haversine(
                    origin_coords[0], origin_coords[1], relay_coords[0], relay_coords[1]
                )
                if dist < min_dist:
                    min_dist = dist
                    best_stealth = relay

        if best_stealth:
            # Second hop: Free region exit
            exit_node = _deterministic_select(free_relays, f"CENSOR-{best_stealth.id}")
            if exit_node:
                # Create 2-hop stealth chain (can be extended to 3-hop if needed)
                chain = create_chain(best_stealth, exit_node, "STEALTH")
                if chain:
                    chains["censorship_resistant"].append(chain)

    # --- CHAIN 6: LOW LATENCY (Speed Optimized) ---
    # Strategy: Fast protocol → Nearby exit with speed optimization
    for exit_node in foreign_exits[:20]:  # Limit
        # Use speed optimization mode
        if exit_node.country_code in COUNTRIES:
            exit_coords = COUNTRIES[exit_node.country_code]
            exit_stub = ProxyStub(
                exit_node.country_code,
                exit_coords[0],
                exit_coords[1],
                exit_node.protocol,
            )

            # Build candidate stubs from fast relays
            relay_stubs = []
            for relay in relays_fast[:30]:
                if relay.country_code in COUNTRIES:
                    coords = COUNTRIES[relay.country_code]
                    relay_stubs.append(
                        ProxyStub(
                            relay.country_code, coords[0], coords[1], relay.protocol
                        )
                    )

            origin_cc = "IR"  # Default origin
            result = find_optimal_relay(
                origin_cc, exit_stub, relay_stubs, optimization_mode="speed"
            )

            if "relay" in result:
                # Find matching proxy
                best_relay = next(
                    (
                        r
                        for r in relays_fast
                        if r.country_code == result["relay"].country
                    ),
                    None,
                )
                if best_relay:
                    chain = create_chain(best_relay, exit_node, "LOWLAT")
                    if chain:
                        chains["low_latency"].append(chain)

    # --- CHAIN 7: HIGH ANONYMITY (Privacy First) ---
    # Strategy: 3-hop chain through different jurisdictions
    # Origin → Relay1 (different continent) → Relay2 (different continent) → Exit
    if len(foreign_exits) >= 3:
        # Group countries by continent/region for diversity
        europe_exits = [
            p
            for p in foreign_exits
            if p.country_code in ["DE", "NL", "GB", "FR", "SE", "CH", "NO"]
        ]
        asia_exits = [
            p for p in foreign_exits if p.country_code in ["SG", "JP", "HK", "KR", "TW"]
        ]
        americas_exits = [
            p for p in foreign_exits if p.country_code in ["US", "CA", "BR", "MX"]
        ]

        # Create 3-hop chains: Asia → Europe → Americas
        for relay1 in asia_exits[:5]:
            relay2 = _deterministic_select(europe_exits, f"ANON1-{relay1.id}")
            exit_node = _deterministic_select(americas_exits, f"ANON2-{relay1.id}")

            if relay2 and exit_node:
                # Build 3-hop chain manually
                r1_out = to_singbox_outbound(relay1)
                r2_out = to_singbox_outbound(relay2)
                exit_out = to_singbox_outbound(exit_node)

                if r1_out and r2_out and exit_out:
                    r1_tag = f"ANON-HOP1-{relay1.id[:6]}"
                    r2_tag = f"ANON-HOP2-{relay2.id[:6]}"
                    exit_tag = f"ANON-EXIT-{exit_node.id[:6]}"

                    r1_out["tag"] = r1_tag
                    r2_out["tag"] = r2_tag
                    r2_out["detour"] = r1_tag
                    exit_out["tag"] = exit_tag
                    exit_out["detour"] = r2_tag
                    exit_out["_process"] = "chain"

                    chains["high_anonymity"].append([r1_out, r2_out, exit_out])

    # --- CHAIN 8: LOAD BALANCED (Alternative Routes) ---
    # Strategy: Create 2-3 alternative routes to popular exits for load distribution
    popular_exits = [
        p for p in foreign_exits if p.country_code in ["US", "DE", "NL", "GB", "SG"]
    ]

    for exit_node in popular_exits[:5]:
        # Create 3 alternative routes to the same exit
        for variant in range(3):
            lb_relay: Optional[Proxy] = _deterministic_select(
                relays_ir if relays_ir else foreign_exits, f"LB{variant}-{exit_node.id}"
            )
            if lb_relay is not None and lb_relay.id != exit_node.id:
                chain = create_chain(lb_relay, exit_node, f"LOADBAL{variant}")
                if chain:
                    chains["load_balanced"].append(chain)

    total_chains = sum(len(v) for v in chains.values())

    logger.info(
        f"Enhanced smart chains generated: {total_chains} chains across {len(chains)} categories. "
        f"intranet={len(chains['intranet'])}, intranet_washed={len(chains['intranet_washed'])}, "
        f"ipv6={len(chains['ipv6'])}, streamer={len(chains['streamer'])}, "
        f"censorship_resistant={len(chains['censorship_resistant'])}, "
        f"low_latency={len(chains['low_latency'])}, high_anonymity={len(chains['high_anonymity'])}, "
        f"load_balanced={len(chains['load_balanced'])}"
    )

    return chains
