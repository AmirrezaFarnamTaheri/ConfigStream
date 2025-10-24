"""Utilities for deterministically sharding proxy identifiers."""

from __future__ import annotations

import hashlib


def shard_for(identifier: str, buckets: int = 256) -> int:
    """Return a shard index for *identifier* in range ``0..buckets-1``."""

    digest = hashlib.blake2b(identifier.encode("utf-8"), digest_size=2).digest()
    value = int.from_bytes(digest, "big")
    return value % buckets
