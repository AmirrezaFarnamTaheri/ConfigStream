# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared network utility helpers used across output and pipeline modules."""

import ipaddress


def normalize_host(value: str) -> str:
    """Normalize a hostname by stripping whitespace and trailing DNS root dot."""
    return value.strip().lower().rstrip(".")


def is_ip_literal(value: str) -> bool:
    """Return True if *value* is a valid IPv4 or IPv6 address literal."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def is_global_ip(value: str) -> bool:
    """Return True if *value* is a globally routable IP address."""
    try:
        return bool(ipaddress.ip_address(value).is_global)
    except ValueError:
        return False
