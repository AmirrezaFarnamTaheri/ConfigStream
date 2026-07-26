# SPDX-License-Identifier: AGPL-3.0-or-later
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from configstream.models import Proxy
from configstream.quality.scoring import (
    calculate_cooldown_hours,
    calculate_diversity_score,
    calculate_trust_score,
)
from configstream.quality.storage import QualityStorage, QualityStorageError


def test_diversity_score():
    assert calculate_diversity_score([]) == 0.0
    proxies = [
        Proxy(country_code="US", protocol="ss", address="a", port=1, config="a")
    ] * 5
    assert calculate_diversity_score(proxies) == 0.0
    proxies = [
        Proxy(country_code="US", protocol="ss", address="a", port=1, config="a"),
        Proxy(country_code="DE", protocol="ss", address="b", port=2, config="b"),
    ]
    assert calculate_diversity_score(proxies) == 0.5


def test_cooldown_hours():
    assert calculate_cooldown_hours(0) == 0.0
    assert calculate_cooldown_hours(1) == 2.0
    assert calculate_cooldown_hours(2) == 4.0
    assert calculate_cooldown_hours(5) == 32.0
    assert calculate_cooldown_hours(10) == 48.0


def test_trust_score():
    assert calculate_trust_score(100.0, 1.0, 0, 0.5) == 100.0
    assert calculate_trust_score(0.0, 0.0, 10, 5.0) == 0.0
    assert calculate_trust_score(100, 1.0, 0, 2.0) == 80.0


def test_storage_init(tmp_path):
    db = tmp_path / "quality.db"
    QualityStorage(db)
    with sqlite3.connect(db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"schema_meta", "source_stats", "source_runs", "proxy_history"} <= tables
        assert (
            conn.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
            is not None
        )


def test_storage_upsert_get(tmp_path):
    storage = QualityStorage(tmp_path / "quality.db")
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
    assert row[3] == 80.0
    assert storage.get_trust_score(url) == 75.0
    stats["trust_score"] = 90.0
    storage.upsert_stats(url, stats)
    assert storage.get_trust_score(url) == 90.0


def test_record_run_is_idempotent(tmp_path):
    storage = QualityStorage(tmp_path / "quality.db")
    url = "https://provider.example/list"
    storage.upsert_stats(url, {"last_checked": 100})
    event = {
        "run_key": "run-1:shard-2:source-3",
        "timestamp": 100,
        "duration_ms": 12.5,
        "fetched_count": 10,
        "working_count": 4,
        "batch_source": "shard-2",
    }
    assert storage.record_run(url, event) is True
    assert storage.record_run(url, event) is False
    with sqlite3.connect(storage.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0] == 1


def test_storage_merge_is_replay_safe(tmp_path):
    db1 = tmp_path / "q1.db"
    db2 = tmp_path / "q2.db"
    destination = QualityStorage(db1)
    source = QualityStorage(db2)
    url = "http://test.com"
    destination.upsert_stats(
        url,
        {
            "total_fetched": 100,
            "total_working": 50,
            "last_checked": 1000,
            "reliability_score": 50.0,
            "trust_score": 50.0,
        },
    )
    source.upsert_stats(
        url,
        {
            "total_fetched": 200,
            "total_working": 100,
            "last_checked": 2000,
            "reliability_score": 80.0,
            "trust_score": 80.0,
        },
    )
    source.record_run(
        url,
        {
            "run_key": "immutable-run-key",
            "timestamp": 2000,
            "fetched_count": 200,
            "working_count": 100,
        },
    )

    destination.merge_from(db2)
    destination.merge_from(db2)

    assert destination.get_trust_score(url) == 80.0
    with sqlite3.connect(db1) as conn:
        assert conn.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0] == 1


def test_storage_missing_merge_source_is_noop(tmp_path):
    storage = QualityStorage(tmp_path / "quality.db")
    storage.merge_from(Path(tmp_path / "missing.db"))


def test_storage_initialization_failure_is_fatal(tmp_path):
    db = tmp_path / "quality.db"
    with patch("sqlite3.connect", side_effect=sqlite3.OperationalError("DB Error")):
        with pytest.raises(
            QualityStorageError, match="failed to open quality database"
        ):
            QualityStorage(db)


def test_storage_write_failure_is_fatal(tmp_path):
    storage = QualityStorage(tmp_path / "quality.db")
    with patch.object(
        storage, "_get_conn", side_effect=sqlite3.OperationalError("locked")
    ):
        with pytest.raises(QualityStorageError, match="failed to update stats"):
            storage.upsert_stats("url", {})
