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
    5: Security Score (if available, else 0)
    6: Stability Score (if available, else 0)
    7: Reliability Score (if available, else 0)
    """

    # 1. Protocol Hash
    h_proto = int(hashlib.md5(proxy.protocol.encode()).hexdigest(), 16) % 10

    # 2. Country Hash
    cc = proxy.country_code or "XX"
    h_country = int(hashlib.md5(cc.encode()).hexdigest(), 16) % 10

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
    h_isp = int(hashlib.md5((proxy.org or "").encode()).hexdigest(), 16) % 10

    return [h_proto, h_country, h_lat, h_port, h_isp, 0, 0, 0]


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
