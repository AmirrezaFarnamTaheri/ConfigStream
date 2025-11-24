import sqlite3
from pathlib import Path
from unittest.mock import patch

from configstream.quality.storage import QualityStorage
from configstream.quality.scoring import (
    calculate_diversity_score,
    calculate_cooldown_hours,
    calculate_trust_score,
)
from configstream.models import Proxy

# --- Scoring Tests ---


def test_diversity_score():
    assert calculate_diversity_score([]) == 0.0

    # All same country
    proxies = [
        Proxy(country_code="US", protocol="ss", address="a", port=1, config="a")
    ] * 5
    assert calculate_diversity_score(proxies) == 0.0

    # Perfect distribution (2 countries)
    proxies = [
        Proxy(country_code="US", protocol="ss", address="a", port=1, config="a"),
        Proxy(country_code="DE", protocol="ss", address="b", port=2, config="b"),
    ]
    # 1 - (0.5^2 + 0.5^2) = 1 - 0.5 = 0.5
    assert calculate_diversity_score(proxies) == 0.5


def test_cooldown_hours():
    assert calculate_cooldown_hours(0) == 0.0
    assert calculate_cooldown_hours(1) == 2.0  # 2^1
    assert calculate_cooldown_hours(2) == 4.0  # 2^2
    assert calculate_cooldown_hours(5) == 32.0
    assert calculate_cooldown_hours(10) == 48.0  # Capped


def test_trust_score():
    # Perfect score
    score = calculate_trust_score(
        reliability_score=100.0,
        diversity_score=1.0,
        consecutive_failures=0,
        avg_jitter=0.5,
    )
    # (50) + (30) + (20) - 0 = 100
    assert score == 100.0

    # Worst score
    score = calculate_trust_score(
        reliability_score=0.0,
        diversity_score=0.0,
        consecutive_failures=10,  # -100 consistency
        avg_jitter=5.0,  # -20 penalty
    )
    # 0 + 0 + 0 - 20 = -20 -> max(0) -> 0
    assert score == 0.0

    # Jitter penalty
    score = calculate_trust_score(100, 1.0, 0, 2.0)
    # 100 - 20 = 80
    assert score == 80.0


# --- Storage Tests ---


def test_storage_init(tmp_path):
    db = tmp_path / "quality.db"
    QualityStorage(db)

    with sqlite3.connect(db) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        assert "source_stats" in tables


def test_storage_upsert_get(tmp_path):
    db = tmp_path / "quality.db"
    storage = QualityStorage(db)

    url = "http://test.com"
    stats = {
        "total_fetched": 100,
        "total_working": 50,
        "consecutive_failures": 0,
        "last_checked": 123456,
        "reliability_score": 80.0,
        "diversity_score": 0.5,
        "trust_score": 75.0,
    }

    storage.upsert_stats(url, stats)

    row = storage.get_source_state(url)
    assert row is not None
    # Check reliability (index 3)
    assert row[3] == 80.0

    assert storage.get_trust_score(url) == 75.0

    # Update
    stats["trust_score"] = 90.0
    storage.upsert_stats(url, stats)
    assert storage.get_trust_score(url) == 90.0


def test_storage_merge(tmp_path):
    db1 = tmp_path / "q1.db"
    db2 = tmp_path / "q2.db"

    s1 = QualityStorage(db1)
    s2 = QualityStorage(db2)

    url = "http://test.com"
    stats1 = {
        "total_fetched": 100,
        "total_working": 50,
        "consecutive_failures": 0,
        "last_checked": 1000,
        "reliability_score": 50.0,
        "diversity_score": 0.5,
        "trust_score": 50.0,
    }
    stats2 = {
        "total_fetched": 200,
        "total_working": 100,
        "consecutive_failures": 0,
        "last_checked": 2000,
        "reliability_score": 80.0,
        "diversity_score": 0.5,
        "trust_score": 80.0,
    }

    s1.upsert_stats(url, stats1)
    s2.upsert_stats(url, stats2)

    # Merge s2 into s1
    s1.merge_from(db2)

    # s1 should now have stats2 because last_checked is newer
    assert s1.get_trust_score(url) == 80.0

    # Test merge invalid path
    s1.merge_from(Path("invalid.db"))


def test_storage_error(tmp_path):
    db = tmp_path / "quality.db"
    # Lock DB to force error?
    # Easier to mock
    with patch("sqlite3.connect", side_effect=Exception("DB Error")):
        storage = QualityStorage(db)
        # Should catch error

        storage.upsert_stats("url", {})
        assert storage.get_trust_score("url") == 50.0
        assert storage.get_source_state("url") is None
