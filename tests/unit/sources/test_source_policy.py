# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta, timezone

from typing import Any, Dict

import pytest

from configstream.sources import (
    SourcePolicyError,
    SourceProvider,
    SourceSnapshotManifest,
    TrustClass,
    validate_snapshot,
)

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)


def provider(**overrides: Any) -> SourceProvider:
    values = {
        "provider_id": "databay",
        "display_name": "Databay",
        "canonical_owner": "databay-labs",
        "canonical_repository": "free-proxy-list",
        "allowed_mirrors": frozenset(),
        "trust_class": TrustClass.OPAQUE,
        "license_spdx": "MIT",
        "declared_protocols": frozenset({"http", "socks4", "socks5"}),
        "max_snapshot_age_seconds": 1800,
        "max_response_bytes": 1_000_000,
        "max_records": 10_000,
        "minimum_records": 1,
    }
    values.update(overrides)
    return SourceProvider(**values)  # type: ignore[arg-type]


def snapshot(**overrides: Any) -> SourceSnapshotManifest:
    values = {
        "run_id": "run-1",
        "provider_id": "databay",
        "requested_locator": "https://github.com/databay-labs/free-proxy-list",
        "resolved_canonical_locator": "https://github.com/databay-labs/free-proxy-list/blob/a/http.txt",
        "repository_owner": "databay-labs",
        "repository_name": "free-proxy-list",
        "ref": "a" * 40,
        "commit_sha": "a" * 40,
        "blob_sha": "b" * 40,
        "content_sha256": "c" * 64,
        "byte_length": 100,
        "record_count": 5,
        "fetched_at": NOW,
        "upstream_commit_time": NOW - timedelta(minutes=5),
        "expires_at": NOW + timedelta(minutes=15),
        "license_spdx": "MIT",
        "protocol_claim": "http",
    }
    values.update(overrides)
    return SourceSnapshotManifest(**values)  # type: ignore[arg-type]


def violation_codes(exc: SourcePolicyError) -> set[str]:
    return {item.code for item in exc.violations}


def test_valid_snapshot_passes():
    validate_snapshot(provider(), snapshot(), now=NOW)


def test_stale_snapshot_is_rejected_before_ingestion():
    stale = snapshot(upstream_commit_time=NOW - timedelta(days=351))
    with pytest.raises(SourcePolicyError) as raised:
        validate_snapshot(provider(), stale, now=NOW)
    assert "snapshot_stale" in violation_codes(raised.value)


def test_unapproved_repository_owner_is_rejected():
    mirror = snapshot(repository_owner="rolandmccarthy13")
    with pytest.raises(SourcePolicyError) as raised:
        validate_snapshot(provider(), mirror, now=NOW)
    assert "repository_owner_mismatch" in violation_codes(raised.value)


def test_explicitly_allowed_mirror_can_pass_identity_check():
    allowed = provider(allowed_mirrors=frozenset({"rolandmccarthy13/free-proxy-list"}))
    mirror = snapshot(repository_owner="rolandmccarthy13")
    validate_snapshot(allowed, mirror, now=NOW)


def test_expired_snapshot_is_rejected():
    expired = snapshot(expires_at=NOW + timedelta(seconds=1))
    with pytest.raises(SourcePolicyError) as raised:
        validate_snapshot(provider(), expired, now=NOW + timedelta(seconds=2))
    assert "snapshot_expired" in violation_codes(raised.value)


def test_size_record_and_license_limits_are_aggregated():
    bad = snapshot(byte_length=1_000_001, record_count=20_000, license_spdx="UNKNOWN")
    with pytest.raises(SourcePolicyError) as raised:
        validate_snapshot(provider(), bad, now=NOW)
    assert violation_codes(raised.value) == {
        "snapshot_too_large",
        "too_many_records",
        "license_mismatch",
    }
