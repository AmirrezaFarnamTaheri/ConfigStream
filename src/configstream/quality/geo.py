import math
from typing import Tuple, Dict

# Country Centroids (approximate Lat, Lon)
# Expanded list for better coverage
COUNTRIES: Dict[str, Tuple[float, float]] = {
    "US": (37.0902, -95.7129),
    "CN": (35.8617, 104.1954),
    "RU": (61.5240, 105.3188),
    "DE": (51.1657, 10.4515),
    "FR": (46.2276, 2.2137),
    "GB": (55.3781, -3.4360),
    "CA": (56.1304, -106.3468),
    "JP": (36.2048, 138.2529),
    "KR": (35.9078, 127.7669),
    "SG": (1.3521, 103.8198),
    "NL": (52.1326, 5.2913),
    "IN": (20.5937, 78.9629),
    "BR": (-14.2350, -51.9253),
    "IR": (32.4279, 53.6880),
    "TR": (38.9637, 35.2433),
    "UA": (48.3794, 31.1656),
    "HK": (22.3193, 114.1694),
    "AU": (-25.2744, 133.7751),
    "IT": (41.8719, 12.5674),
    "ES": (40.4637, -3.7492),
    "PL": (51.9194, 19.1451),
    "ID": (-0.7893, 113.9213),
    "ZA": (-30.5595, 22.9375),
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points on the Earth's surface.
    Returns distance in kilometers.
    """
    R = 6371  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
