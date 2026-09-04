# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the shared public-artifact metadata freshness policy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from configstream.artifact_freshness import validate_metadata_freshness


def test_metadata_freshness_accepts_current_timestamp() -> None:
    metadata = {
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "update_interval_hours": 4,
    }

    assert validate_metadata_freshness(metadata) == []


def test_metadata_freshness_rejects_stale_timestamp() -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    metadata = {
        "generated_at": (now - timedelta(hours=13)).isoformat(),
        "update_interval_hours": 4,
    }

    assert validate_metadata_freshness(metadata, now=now) == [
        "metadata.json is stale (46800s exceeds 43200s freshness limit)"
    ]


def test_metadata_freshness_rejects_invalid_timestamp() -> None:
    assert validate_metadata_freshness({"last_updated_utc": "not-a-date"}) == [
        "metadata.json has an invalid generation timestamp"
    ]


def test_metadata_freshness_uses_newest_valid_timestamp() -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    metadata = {
        "generated_at": (now - timedelta(hours=13)).isoformat(),
        "last_updated_utc": now.isoformat(),
        "update_interval_hours": 4,
    }

    assert validate_metadata_freshness(metadata, now=now) == []


def test_metadata_freshness_treats_naive_timestamp_as_utc() -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    metadata = {
        "last_updated_utc": "2026-09-04T11:30:00",
        "update_interval_hours": 4,
    }

    assert validate_metadata_freshness(metadata, now=now) == []
