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


def validate_metadata_freshness(
    metadata: Mapping[str, Any], *, now: datetime | None = None
) -> list[str]:
    """Return freshness errors for signed-artifact metadata without key material."""

    raw_timestamp = metadata.get("last_updated_utc") or metadata.get("generated_at")
    if not isinstance(raw_timestamp, str) or not raw_timestamp.strip():
        return ["metadata.json missing generated_at or last_updated_utc"]
    try:
        generated_at = datetime.fromisoformat(
            raw_timestamp.strip().replace("Z", "+00:00")
        )
    except ValueError:
        return ["metadata.json has an invalid generation timestamp"]
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        return ["metadata.json generation timestamp must include a timezone"]

    max_age_seconds = metadata_max_age_seconds(metadata)
    if max_age_seconds is None:
        return ["metadata.json update_interval_hours must be a positive number"]

    checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_seconds = (checked_at - generated_at.astimezone(timezone.utc)).total_seconds()
    if age_seconds < -CLOCK_SKEW_TOLERANCE_SECONDS:
        return ["metadata.json generation timestamp is in the future"]
    if age_seconds > max_age_seconds:
        return [
            "metadata.json is stale "
            f"({int(age_seconds)}s exceeds {max_age_seconds}s freshness limit)"
        ]
    return []
