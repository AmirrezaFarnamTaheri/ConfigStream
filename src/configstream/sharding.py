"""Utilities for deterministically sharding proxy identifiers."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def shard_for(identifier: str, buckets: int = 256) -> int:
    """Return a shard index for *identifier* in range ``0..buckets-1``."""

    digest = hashlib.blake2b(identifier.encode("utf-8"), digest_size=2).digest()
    value = int.from_bytes(digest, "big")
    return value % buckets


def save_shard_metadata(
    proxies: List[Any], buckets: int, output_path: Path
) -> Dict[int, int]:
    """
    Save shard distribution metadata for proxies.
    Returns a dict mapping shard_id -> proxy_count.
    """
    shard_counts: Dict[int, int] = {}

    for proxy in proxies:
        proxy_id = getattr(proxy, "id", str(proxy))
        shard_id = shard_for(proxy_id, buckets)
        shard_counts[shard_id] = shard_counts.get(shard_id, 0) + 1

    metadata = {
        "total_proxies": len(proxies),
        "total_buckets": buckets,
        "shard_distribution": {
            str(shard_id): count for shard_id, count in sorted(shard_counts.items())
        },
        "average_per_shard": len(proxies) / buckets if buckets > 0 else 0,
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(
            f"Shard metadata saved: {len(proxies)} proxies across {buckets} buckets"
        )
    except Exception as e:
        logger.error(f"Failed to save shard metadata: {e}")

    return shard_counts
