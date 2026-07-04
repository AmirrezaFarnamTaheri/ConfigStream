# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared parser validation helpers and rejection telemetry.

S-1: Centralizes the host/port validation logic that was previously
duplicated (with subtle inconsistencies) across generic.py, clash_json.py,
extraction.py, openvpn.py, others.py, and shadowsocks.py.  New parser code
should import from this module instead of re-implementing checks.

S-3: Provides lightweight rejection telemetry so that silently dropped
configs become observable.  Every rejection records a (protocol, reason)
pair into an in-process counter that can be inspected via
``get_rejection_stats()`` and is logged in aggregate by the pipeline.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import threading
from collections import Counter
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# RFC 1123 hostname: labels of alphanumerics and hyphens, dot-separated,
# no leading/trailing hyphen per label, total length <= 253.
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)

# ---------------------------------------------------------------------------
# S-3: Rejection telemetry
# ---------------------------------------------------------------------------

_rejections: Counter = Counter()
_rejections_lock = threading.Lock()


def record_rejection(protocol: str, reason: str) -> None:
    """Record a parser rejection for telemetry.

    Args:
        protocol: The protocol being parsed (e.g. "vmess", "ss", "generic").
        reason: Short machine-readable reason (e.g. "invalid_port",
                "invalid_host", "missing_credential", "malformed_base64").
    """
    with _rejections_lock:
        _rejections[(protocol, reason)] += 1


def get_rejection_stats() -> Dict[str, int]:
    """Return aggregated rejection counts keyed as 'protocol:reason'."""
    with _rejections_lock:
        return {
            f"{proto}:{reason}": count for (proto, reason), count in _rejections.items()
        }


def reset_rejection_stats() -> None:
    """Reset telemetry counters (used by tests and between pipeline runs)."""
    with _rejections_lock:
        _rejections.clear()


def log_rejection_summary() -> None:
    """Log an aggregate summary of all recorded rejections.

    Called by the pipeline at the end of a parse phase so that silently
    dropped configs are visible in the run logs.
    """
    stats = get_rejection_stats()
    if not stats:
        logger.info("Parser telemetry: no rejections recorded.")
        return
    total = sum(stats.values())
    top = sorted(stats.items(), key=lambda kv: kv[1], reverse=True)[:10]
    # Build the summary string first so the logger receives a pre-rendered
    # plain string rather than a raw `key` reference (log-sanitization policy).
    summary = ", ".join(f"{reason}={count}" for reason, count in top)
    logger.info(
        "Parser telemetry: %d configs rejected. Top reasons: %s",
        total,
        summary,
    )


# ---------------------------------------------------------------------------
# S-1: Shared validation helpers
# ---------------------------------------------------------------------------


def is_valid_ip(host: str) -> bool:
    """Return True if host is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def is_valid_hostname(host: str) -> bool:
    """Return True if host is a syntactically valid RFC 1123 hostname."""
    if not host or len(host) > 253:
        return False
    return _HOSTNAME_RE.match(host) is not None


def validate_host(
    host: Optional[str],
    protocol: str = "unknown",
    record: bool = True,
) -> bool:
    """Validate a host as either an IP address or hostname.

    Args:
        host: Host string (may include IPv6 brackets).
        protocol: Protocol name for telemetry.
        record: Whether to record a rejection on failure.

    Returns:
        True if the host is a valid IP or hostname.
    """
    if not host or not isinstance(host, str):
        if record:
            record_rejection(protocol, "missing_host")
        return False
    cleaned = host.strip()
    if is_valid_ip(cleaned) or is_valid_hostname(cleaned.strip("[]")):
        return True
    if record:
        record_rejection(protocol, "invalid_host")
    return False


def validate_port(
    port: object,
    protocol: str = "unknown",
    record: bool = True,
) -> Optional[int]:
    """Validate and normalize a port value.

    Accepts int or numeric string. Returns the int port when valid
    (1-65535), otherwise None.

    Args:
        port: The raw port value.
        protocol: Protocol name for telemetry.
        record: Whether to record a rejection on failure.
    """
    try:
        port_val = int(str(port).strip())
    except (ValueError, TypeError):
        if record:
            record_rejection(protocol, "invalid_port_format")
        return None
    if not 1 <= port_val <= 65535:
        if record:
            record_rejection(protocol, "port_out_of_range")
        return None
    return port_val


def validate_host_port(
    host: Optional[str],
    port: object,
    protocol: str = "unknown",
) -> Optional[int]:
    """Validate host and port together.

    Returns the normalized int port when both are valid, otherwise None.
    Telemetry is recorded automatically for each failure mode.
    """
    if not validate_host(host, protocol=protocol):
        return None
    return validate_port(port, protocol=protocol)
