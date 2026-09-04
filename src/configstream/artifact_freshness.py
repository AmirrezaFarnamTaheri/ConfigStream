# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared freshness policy for generated public artifact metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

CLOCK_SKEW_TOLERANCE_SECONDS = 30
MIN_METADATA_MAX_AGE_HOURS = 12.0
MAX_METADATA_MAX_AGE_HOURS = 48.0


def metadata_max_age_seconds(metadata: Mapping[str, Any]) -> int | None:
    """Return the configured metadata age limit, or ``None`` for invalid input."""

    interval = metadata.get("update_interval_hours", 4)
    if isinstance(interval, bool) or not isinstance(interval, (int, float)):
        return None
    if interval <= 0:
        return None
    hours = min(
        MAX_METADATA_MAX_AGE_HOURS,
        max(MIN_METADATA_MAX_AGE_HOURS, float(interval) * 2),
    )
    return int(hours * 60 * 60)


def _parse_metadata_timestamp(value: object) -> datetime | None:
    """Parse one metadata timestamp, treating naive values as UTC."""

    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_metadata_freshness(
    metadata: Mapping[str, Any], *, now: datetime | None = None
) -> list[str]:
    """Return freshness errors for signed-artifact metadata without key material."""

    candidates = [
        _parse_metadata_timestamp(metadata.get("last_updated_utc")),
        _parse_metadata_timestamp(metadata.get("generated_at")),
    ]
    generated_at = max((item for item in candidates if item is not None), default=None)
    if generated_at is None:
        raw_timestamp = metadata.get("last_updated_utc") or metadata.get("generated_at")
        if not isinstance(raw_timestamp, str) or not raw_timestamp.strip():
            return ["metadata.json missing generated_at or last_updated_utc"]
        return ["metadata.json has an invalid generation timestamp"]

    max_age_seconds = metadata_max_age_seconds(metadata)
    if max_age_seconds is None:
        return ["metadata.json update_interval_hours must be a positive number"]

    checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_seconds = (checked_at - generated_at).total_seconds()
    if age_seconds < -CLOCK_SKEW_TOLERANCE_SECONDS:
        return ["metadata.json generation timestamp is in the future"]
    if age_seconds > max_age_seconds:
        return [
            "metadata.json is stale "
            f"({int(age_seconds)}s exceeds {max_age_seconds}s freshness limit)"
        ]
    return []
