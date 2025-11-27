"""
Static Vector Generation.
Generates lightweight feature vectors for proxies to enable client-side similarity search.
Zero-Cost implementation: Uses feature hashing instead of ML embeddings.
"""

import hashlib
import json
import logging
from typing import List, Dict
from pathlib import Path
from ..models import Proxy
from ..utils import AtomicFileWriter

logger = logging.getLogger(__name__)


def _compute_vector(proxy: Proxy) -> List[int]:
    """
    Compute a simple 8-dimension feature vector based on proxy attributes.
    This allows 'similar proxy' finding without an ML model.

    Dimensions:
    0: Protocol (hash mod 10)
    1: Country (hash mod 10)
    2: Latency bucket (0=Fast, 1=Med, 2=Slow)
    3: Port bucket (hash mod 10)
    4: ISP/Org (hash mod 10)
    5: Security Score (0-9 based on protocol and TLS)
    6: Stability Score (default 5)
    7: Reliability Score (default 5)
    """

    # 1. Protocol Hash (use SHA-256 for consistency, even though this is not security-critical)
    h_proto = int(hashlib.sha256(proxy.protocol.encode()).hexdigest(), 16) % 10

    # 2. Country Hash
    cc = proxy.country_code or "XX"
    h_country = int(hashlib.sha256(cc.encode()).hexdigest(), 16) % 10

    # 3. Latency Bucket
    lat = proxy.latency or 9999
    if lat < 150:
        h_lat = 0
    elif lat < 500:
        h_lat = 1
    else:
        h_lat = 2

    # 4. Port Hash
    h_port = proxy.port % 10

    # 5. ISP Hash
    h_isp = int(hashlib.sha256((proxy.org or "").encode()).hexdigest(), 16) % 10

    # 6. Security Score (0-9 based on protocol and TLS)
    security = 0
    if proxy.protocol in ("vless", "trojan"):
        security += 3
    if proxy.details and proxy.details.get("security") in ("tls", "reality"):
        security += 4
    if proxy.details and proxy.details.get("tls") == "tls":
        security += 2
    h_security = min(security, 9)

    # 7-8. Stability and Reliability (default 5 - middle value)
    # Future: integrate with proxy_history for real values
    h_stability = 5
    h_reliability = 5

    return [
        h_proto,
        h_country,
        h_lat,
        h_port,
        h_isp,
        h_security,
        h_stability,
        h_reliability,
    ]


def generate_vectors(proxies: List[Proxy], output_dir: Path) -> None:
    """
    Generate vectors.json for frontend consumption.
    Format: { "proxy_id": [vector] }
    """
    vector_map: Dict[str, List[int]] = {}

    for p in proxies:
        if p.is_working:
            vector_map[p.id] = _compute_vector(p)

    output_file = output_dir / "vectors.json"
    try:
        AtomicFileWriter.write_text(output_file, json.dumps(vector_map))
        logger.info(f"Generated static vectors for {len(vector_map)} proxies")
    except Exception as e:
        logger.error(f"Failed to generate vectors: {e}")
