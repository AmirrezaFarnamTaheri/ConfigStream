# SPDX-License-Identifier: AGPL-3.0-or-later
"""Helpers for safely handling addresses returned by ``socket.getaddrinfo``."""

from __future__ import annotations

from typing import Optional


def normalize_socket_address_host(sockaddr: object) -> Optional[str]:
    """Return a normalized textual host from a ``getaddrinfo`` socket address.

    Typeshed intentionally models the first socket-address element as ``str | int``
    because ``getaddrinfo`` can describe non-IP address families. ConfigStream's
    callers request stream IP addresses, so only non-empty strings are accepted;
    other shapes are ignored rather than coerced into a host.
    """

    if not isinstance(sockaddr, tuple) or not sockaddr:
        return None

    raw_host = sockaddr[0]
    if not isinstance(raw_host, str) or not raw_host:
        return None

    return raw_host.strip("[]")
