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
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from platformdirs import user_cache_path

from .models import Proxy
from .utils import AtomicFileWriter, _FileLock
from .config import AppSettings
from .security_validator import SecurityValidator

logger = logging.getLogger(__name__)


def _find_project_root() -> Optional[Path]:
    """Return the checkout root when running from a source tree."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return None


def _resolve_cache_path(db_path: str | Path) -> Path:
    """Resolve cache storage independently of the process working directory."""
    candidate = Path(db_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    project_root = _find_project_root()
    base = project_root if project_root is not None else user_cache_path("configstream")
    return (base / candidate).resolve()


def _safe_proxy_ref(proxy: Proxy) -> str:
    return SecurityValidator.sanitize_log_message(f"{proxy.address}:{proxy.port}")


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _coerce_nonnegative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(parsed, 0)


def _normalize_entry(value: Any) -> Optional[Dict[str, Any]]:
    """Return a safe cache entry or ``None`` for malformed input."""
    if not isinstance(value, dict):
        return None
    tested_at = _coerce_float(value.get("tested_at"), default=-1.0)
    if tested_at < 0 or tested_at > time.time() + 30:
        return None

    normalized = {key: item for key, item in value.items() if key != "config"}
    normalized["tested_at"] = tested_at
    normalized["test_count"] = _coerce_nonnegative_int(value.get("test_count", 0))
    normalized["success_count"] = _coerce_nonnegative_int(value.get("success_count", 0))
    return normalized


class TestResultCache:
    """JSON-file-backed cache for proxy test results."""

    __test__ = False

    def __init__(
        self,
        db_path: str | Path = "data/test_cache.json",
        ttl_seconds: Optional[int] = None,
        max_entries: Optional[int] = 100_000,
    ):
        """
        Initialize the test result cache.

        Args:
            db_path: Path to the JSON cache file.
            ttl_seconds: Time-to-live for cached results.
            max_entries: Maximum number of newest entries retained on disk.
        """
        self.db_path = _resolve_cache_path(db_path)
        if ttl_seconds is None:
            ttl_seconds = AppSettings().CACHE_TTL
        self.ttl_seconds = int(ttl_seconds)
        self.max_entries = 100_000 if max_entries is None else int(max_entries)
        if self.max_entries <= 0:
            raise ValueError("max_entries must be > 0")
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._tombstones: Dict[str, float] = {}
        self.load()

    def _normalize_cache(self, payload: Any) -> Dict[str, Dict[str, Any]]:
        if not isinstance(payload, dict):
            return {}
        cutoff = time.time() - self.ttl_seconds
        normalized: Dict[str, Dict[str, Any]] = {}
        for key, raw_entry in payload.items():
            entry = _normalize_entry(raw_entry)
            if entry is None or entry["tested_at"] < cutoff:
                continue
            normalized[str(key)] = entry
        return normalized

    def _compact(self, payload: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        newest = sorted(
            payload.items(),
            key=lambda item: (_coerce_float(item[1].get("tested_at")), item[0]),
            reverse=True,
        )[: self.max_entries]
        return dict(newest)

    def load(self) -> None:
        """Load, sanitize, and compact cache contents when the file exists."""
        if not self.db_path.exists():
            logger.info(
                "Cache file not found at %s. Starting with an empty cache.",
                self.db_path,
            )
            return
        try:
            with self.db_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self._cache = self._compact(self._normalize_cache(payload))
            logger.info(
                "Loaded %d entries from cache file: %s",
                len(self._cache),
                self.db_path,
            )
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
            logger.error(
                "Failed to load cache file %s: %s. Starting fresh.",
                self.db_path,
                SecurityValidator.sanitize_log_message(str(exc)),
            )
            self._cache = {}

    def save(self) -> None:
        """Save the current in-memory cache to the JSON file with locking."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock_path = self.db_path.with_suffix(".lock")
            with _FileLock(lock_path):
                self._merge_and_write()
        except OSError as exc:
            logger.error(
                "Failed to save cache file %s: %s",
                self.db_path,
                SecurityValidator.sanitize_log_message(str(exc)),
            )

    def _merge_and_write(self) -> None:
        """Merge concurrent writers by timestamp, then publish a bounded cache."""
        disk_cache: Dict[str, Dict[str, Any]] = {}
        if self.db_path.exists():
            try:
                with self.db_path.open("r", encoding="utf-8") as handle:
                    disk_cache = self._normalize_cache(json.load(handle))
            except (json.JSONDecodeError, OSError, TypeError, ValueError):
                disk_cache = {}

        for tombstone, invalidated_at in self._tombstones.items():
            disk_entry = disk_cache.get(tombstone)
            disk_tested_at = (
                _coerce_float(disk_entry.get("tested_at"))
                if isinstance(disk_entry, dict)
                else 0.0
            )
            if disk_tested_at <= invalidated_at:
                disk_cache.pop(tombstone, None)

        for config_hash, raw_entry in self._cache.items():
            entry = _normalize_entry(raw_entry)
            if entry is None:
                continue
            disk_entry = disk_cache.get(config_hash)
            if disk_entry is None or _coerce_float(
                entry.get("tested_at")
            ) >= _coerce_float(disk_entry.get("tested_at")):
                disk_cache[config_hash] = entry

        self._cache = self._compact(self._normalize_cache(disk_cache))
        content = json.dumps(self._cache, indent=2, sort_keys=True)
        AtomicFileWriter.write_text(self.db_path, content)
        self._tombstones.clear()
        logger.info(
            "Saved %d entries to cache file: %s",
            len(self._cache),
            self.db_path,
        )

    def get(self, proxy: Proxy) -> Optional[Proxy]:
        """Get cached test results for a proxy when the entry is still fresh."""
        if not proxy.config:
            return None

        config_hash = self._compute_hash(proxy.config)
        entry = self._cache.get(config_hash)
        if not entry:
            logger.debug("Cache MISS for %s (no entry)", _safe_proxy_ref(proxy))
            return None

        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds
        tested_at = _coerce_float(entry.get("tested_at"))
        if tested_at < cutoff_time:
            logger.debug("Cache MISS for %s (expired)", _safe_proxy_ref(proxy))
            return None

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
        """Return whether a non-expired cache entry exists without mutating proxy."""
        if not proxy.config:
            return False

        entry = self._cache.get(self._compute_hash(proxy.config))
        if not entry:
            return False
        tested_at = _coerce_float(entry.get("tested_at"))
        return tested_at >= (time.time() - self.ttl_seconds)

    def invalidate(self, proxy: Proxy) -> None:
        """Invalidate/remove a cached result for a proxy."""
        if not proxy.config:
            return
        config_hash = self._compute_hash(proxy.config)
        self._cache.pop(config_hash, None)
        self._tombstones[config_hash] = time.time()

    def set(self, proxy: Proxy) -> None:
        """Store test result metadata without persisting the source config secret."""
        if not proxy.config or proxy.details.get("infra_failure") is True:
            return

        config_hash = self._compute_hash(proxy.config)
        self._tombstones.pop(config_hash, None)
        current_time = time.time()

        existing_entry = self._cache.get(config_hash, {})
        test_count = _coerce_nonnegative_int(existing_entry.get("test_count", 0)) + 1
        success_count = _coerce_nonnegative_int(
            existing_entry.get("success_count", 0)
        ) + (1 if proxy.is_working else 0)

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
        """Get historical success ratio, falling back to a neutral score."""
        if not proxy.config:
            return 0.5

        entry = self._cache.get(self._compute_hash(proxy.config))
        if not entry:
            return 0.5
        test_count = _coerce_nonnegative_int(entry.get("test_count", 0))
        success_count = _coerce_nonnegative_int(entry.get("success_count", 0))
        if test_count <= 0:
            return 0.5
        return min(success_count, test_count) / test_count

    @staticmethod
    def _compute_hash(config: str) -> str:
        """Return a stable hash for a configuration string."""
        return hashlib.sha256(config.encode("utf-8")).hexdigest()

    def cleanup_expired(self) -> int:
        """Remove expired or malformed entries from the in-memory cache."""
        initial_count = len(self._cache)
        self._cache = self._compact(self._normalize_cache(self._cache))
        deleted = initial_count - len(self._cache)
        if deleted > 0:
            logger.info("Cleaned up %d expired entries", deleted)
        return deleted

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics using normalized numeric counters."""
        cutoff_time = time.time() - self.ttl_seconds
        valid_entries = 0
        total_health = 0.0
        valid_health_count = 0

        for entry in self._cache.values():
            tested_at = _coerce_float(entry.get("tested_at"))
            if tested_at < cutoff_time:
                continue
            valid_entries += 1
            test_count = _coerce_nonnegative_int(entry.get("test_count", 0))
            success_count = _coerce_nonnegative_int(entry.get("success_count", 0))
            if test_count > 0:
                total_health += min(success_count, test_count) / test_count
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
        """Merge another cache into this one, keeping newest results on conflict."""
        for config_hash, raw_entry in other_cache._cache.items():
            other_entry = _normalize_entry(raw_entry)
            if other_entry is None:
                continue
            existing_entry = self._cache.get(config_hash)
            if existing_entry is None or _coerce_float(
                other_entry.get("tested_at")
            ) > _coerce_float(existing_entry.get("tested_at")):
                self._cache[config_hash] = other_entry
        self._cache = self._compact(self._normalize_cache(self._cache))
