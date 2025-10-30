"""Freshness and TTL helpers for proxies."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def apply_ttl(
    proxy: Any, now: datetime | None = None, ttl_hours: int = 24, drop_hours: int = 48
) -> bool:
    """Mark ``proxy`` stale depending on the age of ``tested_at``.

    Returns ``True`` if the proxy should be kept, ``False`` if it should be dropped
    because it has exceeded ``drop_hours``.
    """

    if now is None:
        now = datetime.now(timezone.utc)

    if not proxy.tested_at:
        proxy.age_seconds = 0
        proxy.stale = False
        return True

    if isinstance(proxy.tested_at, str):
        try:
            tested = datetime.fromisoformat(proxy.tested_at.replace("Z", "+00:00"))
        except ValueError:
            proxy.age_seconds = 0
            proxy.stale = False
            return True
    else:
        tested = proxy.tested_at

    age = (now - tested).total_seconds()
    proxy.age_seconds = int(age)
    stale_seconds = ttl_hours * 3600
    drop_seconds = drop_hours * 3600

    proxy.stale = age > stale_seconds
    return age <= drop_seconds
