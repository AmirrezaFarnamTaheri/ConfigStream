# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import time
from pathlib import Path
import pytest

from configstream.models import Proxy
from configstream.test_cache import TestResultCache


@pytest.mark.parametrize("timestamp", ["NaN", "Infinity", "-Infinity", 1e300])
def test_invalid_timestamp_does_not_poison_cache(
    tmp_path: Path, timestamp: object
) -> None:
    path = tmp_path / "cache.json"
    proxy = _proxy(1)
    key = TestResultCache._compute_hash(proxy.config)
    path.write_text(json.dumps({key: {"tested_at": timestamp}}), encoding="utf-8")
    cache = TestResultCache(path)
    assert cache.get(proxy) is None
    assert not cache.contains(proxy)


def test_infinite_counters_preserve_other_valid_cache_entries(tmp_path: Path) -> None:
    path = tmp_path / "cache.json"
    path.write_text(
        json.dumps(
            {
                "valid": {"tested_at": time.time(), "test_count": float("inf")},
                "other": {"tested_at": time.time()},
            }
        ),
        encoding="utf-8",
    )
    cache = TestResultCache(path)
    assert set(cache._cache) == {"valid", "other"}
    assert cache._cache["valid"]["test_count"] == 0


def _proxy(index: int) -> Proxy:
    return Proxy(
        config=f"vless://00000000-0000-0000-0000-{index:012d}@1.1.1.{index}:443",
        protocol="vless",
        address=f"1.1.1.{index}",
        port=443,
        uuid=f"00000000-0000-0000-0000-{index:012d}",
    )


def test_save_compacts_to_newest_bounded_entries(tmp_path):
    path = tmp_path / "cache.json"
    cache = TestResultCache(path, ttl_seconds=3600, max_entries=2)
    for index in range(1, 4):
        proxy = _proxy(index)
        proxy.is_working = True
        cache.set(proxy)
        cache._cache[cache._compute_hash(proxy.config)]["tested_at"] = (
            time.time() + index
        )
    cache.save()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert all("config" not in entry for entry in payload.values())
    assert cache.contains(_proxy(1)) is False
    assert cache.contains(_proxy(2)) is True
    assert cache.contains(_proxy(3)) is True


def test_load_discards_expired_and_invalid_entries(tmp_path):
    path = tmp_path / "cache.json"
    fresh = time.time()
    path.write_text(
        json.dumps(
            {
                "expired": {"tested_at": fresh - 5000},
                "fresh": {"tested_at": fresh, "config": "vless://secret@example"},
                "invalid": "not-an-entry",
            }
        ),
        encoding="utf-8",
    )
    cache = TestResultCache(path, ttl_seconds=60, max_entries=10)
    assert set(cache._cache) == {"fresh"}
    assert "config" not in cache._cache["fresh"]


def test_concurrent_save_does_not_overwrite_newer_disk_result(tmp_path):
    path = tmp_path / "cache.json"
    proxy = _proxy(1)

    stale_writer = TestResultCache(path, ttl_seconds=3600, max_entries=10)
    proxy.is_working = False
    stale_writer.set(proxy)
    key = stale_writer._compute_hash(proxy.config)
    stale_writer._cache[key]["tested_at"] = time.time() - 30

    fresh_writer = TestResultCache(path, ttl_seconds=3600, max_entries=10)
    proxy.is_working = True
    fresh_writer.set(proxy)
    fresh_writer._cache[key]["tested_at"] = time.time()
    fresh_writer.save()

    stale_writer.save()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload[key]["is_working"] == 1
    assert payload[key]["tested_at"] == fresh_writer._cache[key]["tested_at"]


def test_numeric_string_timestamps_do_not_crash_cache_queries(tmp_path):
    path = tmp_path / "cache.json"
    proxy = _proxy(1)
    key = TestResultCache._compute_hash(proxy.config)
    now = time.time()
    path.write_text(
        json.dumps(
            {
                key: {
                    "tested_at": str(now),
                    "is_working": 1,
                    "test_count": "2",
                    "success_count": "1",
                }
            }
        ),
        encoding="utf-8",
    )

    cache = TestResultCache(path, ttl_seconds=60, max_entries=10)

    assert cache.contains(proxy) is True
    assert cache.get(proxy) is proxy
    assert cache.get_health_score(proxy) == 0.5
    assert cache.get_stats()["valid_entries"] == 1


def test_malformed_health_counters_are_safely_normalized(tmp_path):
    cache = TestResultCache(tmp_path / "cache.json", ttl_seconds=60, max_entries=10)
    proxy = _proxy(1)
    key = cache._compute_hash(proxy.config)
    cache._cache[key] = {
        "tested_at": time.time(),
        "test_count": "not-a-number",
        "success_count": object(),
    }

    assert cache.get_health_score(proxy) == 0.5
    proxy.is_working = True
    cache.set(proxy)
    assert cache._cache[key]["test_count"] == 1
    assert cache._cache[key]["success_count"] == 1


def test_merge_compares_string_and_float_timestamps_safely(tmp_path):
    proxy = _proxy(1)
    key = TestResultCache._compute_hash(proxy.config)
    older = TestResultCache(tmp_path / "older.json", ttl_seconds=60, max_entries=10)
    newer = TestResultCache(tmp_path / "newer.json", ttl_seconds=60, max_entries=10)
    older._cache[key] = {"tested_at": str(time.time() - 5), "is_working": 0}
    newer._cache[key] = {"tested_at": time.time(), "is_working": 1}

    older.merge(newer)

    assert older._cache[key]["is_working"] == 1
