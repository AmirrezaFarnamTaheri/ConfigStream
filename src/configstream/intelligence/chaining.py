from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

try:
    from geopy.distance import geodesic  # type: ignore

    GEOPY_AVAILABLE = True
except ImportError:
    logger.warning(
        "geopy not installed - optimal relay selection disabled. Install with: pip install geopy"
    )
    GEOPY_AVAILABLE = False

    # Fallback haversine distance calculation
    def geodesic(coord1, coord2):
        """Fallback distance calculation using haversine formula."""
        import math

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

        class Distance:
            def __init__(self, km):
                self.km = km

        return Distance(R * c)


# Minimal Proxy definition for typing
class ProxyStub:
    def __init__(self, country: str, lat: float, lon: float, protocol: str):
        self.country = country
        self.lat = lat
        self.lon = lon
        self.protocol = protocol


# Expanded list of country coordinates (approximate center lat/lon)
# Includes censored origins, strategic relays, and major exit nodes.
COUNTRIES = {
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


def find_optimal_relay(
    origin_cc: str, exit_node: ProxyStub, candidates: List[ProxyStub]
) -> Dict[str, Any]:
    """
    Finds the best relay node between origin and exit node using geodesic distance.
    Returns the best relay proxy and metadata.
    """
    if origin_cc not in COUNTRIES:
        logger.warning(
            f"Geodesic optimization skipped: Origin country '{origin_cc}' not in coordinate database."
        )
        return {"error": f"Unknown origin country: {origin_cc}"}

    origin_coords = COUNTRIES[origin_cc]
    exit_coords = (exit_node.lat, exit_node.lon)

    best_relay = None
    min_score = float("inf")

    # Direct distance for comparison
    direct_dist = geodesic(origin_coords, exit_coords).km

    for relay in candidates:
        if relay.country == origin_cc or relay.country == exit_node.country:
            continue

        relay_coords = (relay.lat, relay.lon)

        # Calculate total path length
        d1 = geodesic(origin_coords, relay_coords).km
        d2 = geodesic(relay_coords, exit_coords).km
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
