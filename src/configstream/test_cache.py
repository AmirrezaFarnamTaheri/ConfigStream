# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test result caching system for ConfigStream.

This module provides a JSON-file-based cache for proxy test results,
significantly reducing retest time by skipping recently validated proxies.
It is designed to work with CI artifact passing rather than a persistent DB.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .models import Proxy
from .utils import AtomicFileWriter, _FileLock
from .config import AppSettings
from .security_validator import SecurityValidator

logger = logging.getLogger(__name__)


def _safe_proxy_ref(proxy: Proxy) -> str:
    return SecurityValidator.sanitize_log_message(f"{proxy.address}:{proxy.port}")


class TestResultCache:
    """JSON-file-backed cache for proxy test results."""

    __test__ = False

    def __init__(
        self, db_path: str = "data/test_cache.json", ttl_seconds: Optional[int] = None
    ):
        """
        Initialize the test result cache.

        Args:
            db_path: Path to the JSON cache file.
            ttl_seconds: Time-to-live for cached results (default: 1 hour).
        """
        self.db_path = Path(db_path)
        if ttl_seconds is None:
            ttl_seconds = AppSettings().CACHE_TTL
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._tombstones: set[str] = set()
        self.load()

    def load(self) -> None:
        """Load cache from the JSON file if it exists."""
        if not self.db_path.exists():
            logger.info(
                "Cache file not found at %s. Starting with an empty cache.",
                self.db_path,
            )
            return
        try:
            with self.db_path.open("r", encoding="utf-8") as f:
                self._cache = json.load(f)
            logger.info(
                "Loaded %d entries from cache file: %s",
                len(self._cache),
                self.db_path,
            )
        except (json.JSONDecodeError, IOError) as e:
            logger.error(
                "Failed to load cache file %s: %s. Starting fresh.",
                self.db_path,
                SecurityValidator.sanitize_log_message(str(e)),
            )
            self._cache = {}

    def save(self) -> None:
        """Save the current in-memory cache to the JSON file with locking."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock_path = self.db_path.with_suffix(".lock")
            with _FileLock(lock_path):
                self._merge_and_write()

        except IOError as e:
            logger.error(
                "Failed to save cache file %s: %s",
                self.db_path,
                SecurityValidator.sanitize_log_message(str(e)),
            )

    def _merge_and_write(self):
        # Re-load to ensure we merge changes if another process wrote recently
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    disk_cache = json.load(f)
                    # Apply tombstones to remove invalidated entries from disk cache
                    for tombstone in self._tombstones:
                        disk_cache.pop(tombstone, None)
                    # Merge in-memory cache into disk cache (in-memory takes precedence)
                    disk_cache.update(self._cache)
                    self._cache = disk_cache
            except (json.JSONDecodeError, IOError):
                pass

        content = json.dumps(self._cache, indent=2)
        AtomicFileWriter.write_text(self.db_path, content)
        logger.info(
            "Saved %d entries to cache file: %s",
            len(self._cache),
            self.db_path,
        )

    def get(self, proxy: Proxy) -> Optional[Proxy]:
        """
        Get cached test result for a proxy.

        Args:
            proxy: Proxy to look up.

        Returns:
            Cached proxy with test results, or None if not cached or expired.
        """
        if not proxy.config:
            return None

        config_hash = self._compute_hash(proxy.config)
        entry = self._cache.get(config_hash)

        if not entry:
            logger.debug("Cache MISS for %s (no entry)", _safe_proxy_ref(proxy))
            return None

        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds
        tested_at = entry.get("tested_at", 0.0)

        if tested_at < cutoff_time:
            logger.debug("Cache MISS for %s (expired)", _safe_proxy_ref(proxy))
            return None

        # Update proxy with cached results
        proxy.is_working = bool(entry.get("is_working", False))
        proxy.latency = entry.get("latency")
        proxy.country = entry.get("country") or proxy.country
        proxy.country_code = entry.get("country_code") or proxy.country_code
        proxy.city = entry.get("city") or proxy.city
        proxy.tested_at = datetime.fromtimestamp(tested_at, tz=timezone.utc).isoformat()

        logger.debug(
            "Cache HIT for %s (age: %.1fs)",
            _safe_proxy_ref(proxy),
            current_time - tested_at,
        )
        return proxy

    def contains(self, proxy: Proxy) -> bool:
        """
        Return True if a non-expired cache entry exists for the proxy.

        Unlike :meth:`get`, this performs a pure membership/TTL check and does
        NOT mutate the passed proxy (``get`` copies cached results onto it as a
        side effect). Use this when you only need existence, e.g. cache warming.
        """
        if not proxy.config:
            return False

        entry = self._cache.get(self._compute_hash(proxy.config))
        if not entry:
            return False

        tested_at = entry.get("tested_at", 0.0)
        return tested_at >= (time.time() - self.ttl_seconds)

    def invalidate(self, proxy: Proxy) -> None:
        """Invalidate/remove a cached result for a proxy."""
        if not proxy.config:
            return
        config_hash = self._compute_hash(proxy.config)
        self._cache.pop(config_hash, None)
        self._tombstones.add(config_hash)

    def set(self, proxy: Proxy) -> None:
        """
        Store test result in cache.

        Args:
            proxy: Proxy with test results to cache.
        """
        if not proxy.config or proxy.details.get("infra_failure") is True:
            return

        config_hash = self._compute_hash(proxy.config)
        self._tombstones.discard(config_hash)
        current_time = time.time()

        existing_entry = self._cache.get(config_hash, {})
        test_count = existing_entry.get("test_count", 0) + 1
        success_count = existing_entry.get("success_count", 0) + (
            1 if proxy.is_working else 0
        )

        self._cache[config_hash] = {
            "config": proxy.config,
            "is_working": int(proxy.is_working),
            "latency": proxy.latency,
            "country": proxy.country,
            "country_code": proxy.country_code,
            "city": proxy.city,
            "tested_at": current_time,
            "test_count": test_count,
            "success_count": success_count,
        }

    def get_health_score(self, proxy: Proxy) -> float:
        """
        Get health score for a proxy based on historical test results.

        Args:
            proxy: Proxy to get health score for.

        Returns:
            Health score between 0.0 and 1.0 (1.0 = always working).
        """
        if not proxy.config:
            return 0.5  # Default neutral score

        config_hash = self._compute_hash(proxy.config)
        entry = self._cache.get(config_hash)

        if entry and entry.get("test_count", 0) > 0:
            return float(entry["success_count"]) / float(entry["test_count"])

        return 0.5  # Default neutral score for new proxies

    @staticmethod
    def _compute_hash(config: str) -> str:
        """Return a stable hash for a configuration string."""
        digest = hashlib.sha256(config.encode("utf-8")).hexdigest()
        return digest

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from the in-memory cache.

        Returns:
            Number of entries removed.
        """
        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds

        initial_count = len(self._cache)
        self._cache = {
            h: entry
            for h, entry in self._cache.items()
            if entry.get("tested_at", 0.0) >= cutoff_time
        }
        deleted = initial_count - len(self._cache)

        if deleted > 0:
            logger.info("Cleaned up %d expired cache entries", deleted)

        return deleted

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds

        valid_entries = 0
        total_health = 0.0
        valid_health_count = 0

        for entry in self._cache.values():
            if entry.get("tested_at", 0.0) >= cutoff_time:
                valid_entries += 1
                if entry.get("test_count", 0) > 0:
                    total_health += float(entry["success_count"]) / float(
                        entry["test_count"]
                    )
                    valid_health_count += 1

        avg_health = (
            total_health / valid_health_count if valid_health_count > 0 else 0.0
        )

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "average_health_score": round(avg_health, 3),
            "ttl_seconds": self.ttl_seconds,
        }

    def merge(self, other_cache: "TestResultCache") -> None:
        """
        Merge another cache into this one, keeping the newest results on conflict.
        """
        # pylint: disable=protected-access
        for config_hash, other_entry in other_cache._cache.items():
            existing_entry = self._cache.get(config_hash)
            if not existing_entry or other_entry.get(
                "tested_at", 0
            ) > existing_entry.get("tested_at", 0):
                self._cache[config_hash] = other_entry
