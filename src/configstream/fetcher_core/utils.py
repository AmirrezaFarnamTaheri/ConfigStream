"""
Helper functions for fetcher.
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def parse_retry_after(header: str | None) -> float | None:
    """Parse Retry-After header to seconds."""
    if not header:
        return None
    try:
        if header.isdigit():
            return float(header)
        parsed = parsedate_to_datetime(header)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (parsed - now).total_seconds())
    except Exception:
        return None
