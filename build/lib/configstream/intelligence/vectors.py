# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Static Vector Generation.
Generates lightweight feature vectors for proxies to enable client-side similarity search.
Zero-Cost implementation: Uses feature hashing instead of ML embeddings.
"""

import hashlib
import json
import logging
from typing import List, Dict, Optional, TYPE_CHECKING
from pathlib import Path
from configstream.models import Proxy
from configstream.utils import AtomicFileWriter
from configstream.utils.bool_parser import parse_tls_flag
from configstream.security_validator import SecurityValidator

if TYPE_CHECKING:
    from configstream.history.tracker import ProxyHistoryTracker

logger = logging.getLogger(__name__)


def _compute_vector(
    proxy: Proxy,
    history_stats: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[int]:
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
    proto = (proxy.protocol or "unknown").lower()
    h_proto = int(hashlib.sha256(proto.encode()).hexdigest(), 16) % 10

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
    port_value = proxy.port if isinstance(proxy.port, int) else 0
    h_port = int(port_value) % 10

    # 5. ISP Hash
    h_isp = int(hashlib.sha256((proxy.org or "").encode()).hexdigest(), 16) % 10

    # 6. Security Score (0-9 based on protocol and TLS)
    security = 0
    if proto in ("vless", "trojan"):
        security += 3
    if isinstance(proxy.details, dict):
        security_value = proxy.details.get("security")
        if isinstance(security_value, str) and security_value.lower() in (
            "tls",
            "reality",
        ):
            security += 4
        if parse_tls_flag(proxy.details.get("tls")):
            security += 2
    h_security = min(security, 9)

    # 7-8. Stability and Reliability (0-9)
    # Use proxy_history when available; default 5 (middle) otherwise
    h_stability = 5
    h_reliability = 5
    if history_stats and proxy.id:
        stats = history_stats.get(proxy.id)
        if stats:
            rel = stats.get("reliability")
            if rel is not None:
                h_reliability = min(9, max(0, int(round(rel * 10))))
                h_stability = h_reliability  # Same source: success rate

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


def generate_vectors(
    proxies: List[Proxy],
    output_dir: Path,
    history: Optional["ProxyHistoryTracker"] = None,
) -> None:
    """
    Generate vectors.json for frontend consumption.
    Format: { "proxy_id": [vector] }
    When history is provided, stability/reliability dimensions use real success-rate data.
    """
    vector_map: Dict[str, List[int]] = {}
    history_stats: Optional[Dict[str, Dict[str, float]]] = None
    if history:
        working_ids = [p.id for p in proxies if p.is_working and p.id]
        if working_ids:
            history_stats = history.get_bulk_stats(working_ids)

    for p in proxies:
        if p.is_working:
            vector_map[p.id] = _compute_vector(p, history_stats)

    output_file = output_dir / "vectors.json"
    try:
        AtomicFileWriter.write_text(
            output_file, json.dumps(vector_map, ensure_ascii=False)
        )
        logger.info("Generated static vectors for %s proxies", len(vector_map))
    except Exception as e:
        logger.error(
            "Failed to generate vectors: %s",
            SecurityValidator.sanitize_log_message(str(e)),
        )
