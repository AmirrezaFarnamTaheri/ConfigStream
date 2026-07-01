# SPDX-License-Identifier: AGPL-3.0-or-later
from .manager import VwarpTool
from .constants import (
    PSIPHON_COUNTRY_CODES,
    MASQUE_NOIZE_PRESETS,
    ATOMICNOIZE_PRESETS,
    DEFAULT_WARP_ENDPOINT,
)
from configstream.security_validator import SecurityValidator


def _sanitize_process_output(value: object, limit: int = 2048) -> str:
    """Decode, sanitize, and bound subprocess output before logging/storing it."""
    if isinstance(value, bytes):
        text = value.decode(errors="ignore")
    else:
        text = str(value)
    text = SecurityValidator.sanitize_log_message(text)
    if len(text) > limit:
        return f"{text[:limit]}...[truncated]"
    return text


__all__ = [
    "VwarpTool",
    "PSIPHON_COUNTRY_CODES",
    "MASQUE_NOIZE_PRESETS",
    "ATOMICNOIZE_PRESETS",
    "DEFAULT_WARP_ENDPOINT",
    "_sanitize_process_output",
]
