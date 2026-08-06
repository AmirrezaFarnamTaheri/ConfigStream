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


def _tested_at(entry: Dict[str, Any]) -> float:
    try:
        return float(entry.get("tested_at", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _nonnegative_int(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0


def _health_counts(entry: Dict[str, Any]) -> tuple[int, int]:
    tests = _nonnegative_int(entry.get("test_count", 0))
    successes = min(tests, _nonnegative_int(entry.get("success_count", 0)))
    return tests, successes


def _without_sensitive_config(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Return a cache entry without the original credential-bearing URI."""

    sanitized = dict(entry)
    sanitized.pop("config", None)
    return sanitized


class TestResultCache:
    """JSON-file-backed cache for proxy test results."""

    __test__ = False

    def __init__(
        self,
        db_path: str = "data/test_cache.json",
        ttl_seconds: Optional[int] = None,
        max_entries: Optional[int] = None,
    ):
        """
        Initialize the test result cache.

        Args:
            db_path: Path to the JSON cache file.
            ttl_seconds: Time-to-live for cached results (default: 1 hour).
        """
        self.db_path = Path(db_path)
        settings = AppSettings()
        if ttl_seconds is None:
            ttl_seconds = settings.CACHE_TTL
        if max_entries is None:
            max_entries = settings.CACHE_MAX_ENTRIES
        if int(max_entries) <= 0:
            raise ValueError("max_entries must be > 0")
        self.ttl_seconds = ttl_seconds
        self.max_entries = int(max_entries)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._tombstones: Dict[str, float] = {}
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
                payload = json.load(f)
            if not isinstance(payload, dict):
                raise json.JSONDecodeError("cache root must be an object", "", 0)
            self._cache = {
                str(key): _without_sensitive_config(value)
                for key, value in payload.items()
                if isinstance(value, dict)
            }
            self._compact()
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
                    if not isinstance(disk_cache, dict):
                        raise ValueError("cache root must be an object")
                    disk_cache = {
                        str(key): _without_sensitive_config(value)
                        for key, value in disk_cache.items()
                        if isinstance(value, dict)
                    }
                    # Apply only tombstones that are at least as new as the
                    # corresponding disk entry. A newer result from another
                    # writer must survive an older invalidation.
                    for tombstone, invalidated_at in self._tombstones.items():
                        disk_entry = disk_cache.get(tombstone)
                        try:
                            disk_tested_at = (
                                float(disk_entry.get("tested_at", 0.0))
                                if isinstance(disk_entry, dict)
                                else 0.0
                            )
                        except (TypeError, ValueError):
                            disk_tested_at = 0.0
                        if disk_tested_at <= invalidated_at:
                            disk_cache.pop(tombstone, None)
                    # Prefer the newest result per key. A long-lived process
                    # may still hold the entry it loaded at startup; blindly
                    # applying it would overwrite a newer result written by a
                    # concurrent process despite holding the file lock here.
                    for key, memory_entry in self._cache.items():
                        disk_entry = disk_cache.get(key)
                        if not isinstance(disk_entry, dict) or _tested_at(
                            memory_entry
                        ) >= _tested_at(disk_entry):
                            disk_cache[key] = _without_sensitive_config(memory_entry)
                    self._cache = disk_cache
            except (json.JSONDecodeError, IOError, ValueError):
                pass

        self._compact()
        self._cache = {
            key: _without_sensitive_config(entry)
            for key, entry in self._cache.items()
        }
        content = json.dumps(self._cache, indent=2, sort_keys=True)
        AtomicFileWriter.write_text(self.db_path, content)
        # Tombstones describe pending deletions. Once the atomic write succeeds,
        # retaining them would let a later unrelated save delete newer results.
        self._tombstones.clear()
        logger.info(
            "Saved %d entries to cache file: %s",
            len(self._cache),
            self.db_path,
        )

    def _compact(self) -> int:
        """Bound the JSON snapshot by TTL and newest-entry retention."""
        now = time.time()
        cutoff = now - self.ttl_seconds
        before = len(self._cache)
        valid = {
            key: entry
            for key, entry in self._cache.items()
            if _tested_at(entry) >= cutoff
        }
        if len(valid) > self.max_entries:
            ordered = sorted(
                valid.items(),
                key=lambda item: (_tested_at(item[1]), item[0]),
                reverse=True,
            )
            valid = dict(ordered[: self.max_entries])
        self._cache = valid
        removed = before - len(valid)
        if removed:
            logger.info(
                "Compacted %d cache entries; retained %d (limit=%d)",
                removed,
                len(valid),
                self.max_entries,
            )
        return removed

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
        tested_at = _tested_at(entry)

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

        tested_at = _tested_at(entry)
        return tested_at >= (time.time() - self.ttl_seconds)

    def invalidate(self, proxy: Proxy) -> None:
        """Invalidate/remove a cached result for a proxy."""
        if not proxy.config:
            return
        config_hash = self._compute_hash(proxy.config)
        self._cache.pop(config_hash, None)
        self._tombstones[config_hash] = time.time()

    def set(self, proxy: Proxy) -> None:
        """
        Store test result in cache.

        Args:
            proxy: Proxy with test results to cache.
        """
        if not proxy.config or proxy.details.get("infra_failure") is True:
            return

        config_hash = self._compute_hash(proxy.config)
        self._tombstones.pop(config_hash, None)
        current_time = time.time()

        existing_entry = self._cache.get(config_hash, {})
        test_count, success_count = _health_counts(existing_entry)
        test_count += 1
        success_count += 1 if proxy.is_working else 0

        self._cache[config_hash] = {
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

        if entry:
            test_count, success_count = _health_counts(entry)
            if test_count > 0:
                return success_count / test_count

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
            if _tested_at(entry) >= cutoff_time
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
            if _tested_at(entry) >= cutoff_time:
                valid_entries += 1
                test_count, success_count = _health_counts(entry)
                if test_count > 0:
                    total_health += success_count / test_count
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
            if not existing_entry or _tested_at(other_entry) > _tested_at(existing_entry):
                self._cache[config_hash] = other_entry
