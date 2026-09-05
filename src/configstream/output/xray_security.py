# SPDX-License-Identifier: AGPL-3.0-or-later
"""Transport requirements of the pinned Xray native validator.

The private destinations intentionally match Xray rather than Python's
version-dependent ``ipaddress.is_private`` classification:
https://github.com/XTLS/Xray-core/blob/v26.7.28/common/geodata/consts.go
https://github.com/XTLS/Xray-core/blob/v26.7.28/infra/conf/xray.go
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any

from configstream.utils.net import normalize_host

XRAY_PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.88.99.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/3",
        "::/127",
        "fc00::/7",
        "fe80::/10",
        "ff00::/8",
    )
)
XRAY_PRIVATE_DOMAINS = (
    "lan",
    "localdomain",
    "example",
    "invalid",
    "localhost",
    "test",
    "local",
    "home.arpa",
    "internal",
)
_SINGLE_LABEL_DOMAIN = re.compile(r"^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$")


def requires_transport_security(address: Any) -> bool:
    """Return whether Xray requires encryption for this destination."""
    if not isinstance(address, str) or not address.strip():
        return True
    host = normalize_host(address).strip("[]")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return not (
            _SINGLE_LABEL_DOMAIN.fullmatch(host)
            or any(
                host == suffix or host.endswith("." + suffix)
                for suffix in XRAY_PRIVATE_DOMAINS
            )
        )
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not any(ip in network for network in XRAY_PRIVATE_NETWORKS)


def transport_security_error(
    protocol: str, settings: dict[str, Any], stream: dict[str, Any]
) -> str | None:
    """Reject plaintext Trojan/VLESS public outbounds before native checks."""
    if protocol not in {"trojan", "vless"}:
        return None
    if stream.get("security") in ("tls", "reality"):
        return None
    if protocol == "vless" and settings.get("encryption") not in (None, "", "none"):
        return None
    if requires_transport_security(settings.get("address")):
        return f"{protocol} public destinations require TLS or protocol encryption"
    return None
