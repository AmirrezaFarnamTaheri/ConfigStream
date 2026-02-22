# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Memory-bounded Bloom filter for large-scale deduplication in ingestion paths.
"""

from __future__ import annotations

import hashlib
import math


class BloomFilter:
    """
    Compact probabilistic set with fixed memory usage.

    False positives are possible, false negatives are not.
    """

    def __init__(
        self,
        expected_items: int = 2_000_000,
        false_positive_rate: float = 0.001,
    ) -> None:
        n = max(1, int(expected_items))
        p = min(0.999999, max(1e-9, float(false_positive_rate)))

        bit_count = int(-(n * math.log(p)) / (math.log(2) ** 2))
        hash_count = int((bit_count / n) * math.log(2))

        self.bit_count = max(8, bit_count)
        self.hash_count = max(2, hash_count)
        self._bits = bytearray((self.bit_count + 7) // 8)

    @staticmethod
    def _to_bytes(value: str) -> bytes:
        return value.encode("utf-8", errors="ignore")

    def _indexes(self, value: str):
        data = self._to_bytes(value)
        digest_a = hashlib.sha256(data).digest()
        digest_b = hashlib.blake2b(data, digest_size=16).digest()

        h1 = int.from_bytes(digest_a[:8], "big", signed=False)
        h2 = int.from_bytes(digest_b[:8], "big", signed=False) or 1

        for i in range(self.hash_count):
            yield (h1 + i * h2) % self.bit_count

    def add(self, value: str) -> None:
        for idx in self._indexes(value):
            self._bits[idx >> 3] |= 1 << (idx & 7)

    def __contains__(self, value: str) -> bool:
        for idx in self._indexes(value):
            if not (self._bits[idx >> 3] & (1 << (idx & 7))):
                return False
        return True
