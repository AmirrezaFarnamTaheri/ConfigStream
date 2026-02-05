# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from typing import Dict, Any, List


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


# Curated resolvers based on public, free providers.
# Sources inspired by the added DNS tools and DoH worker lists.
DEFAULT_DOH = _dedupe(
    [
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/dns-query",
        "https://dns.quad9.net/dns-query",
        "https://dns.adguard.com/dns-query",
        "https://doh.opendns.com/dns-query",
        "https://adblock.dns.mullvad.net/dns-query",
    ]
)

DEFAULT_DOT = _dedupe(
    [
        "tls://1.1.1.1",
        "tls://1.0.0.1",
        "tls://8.8.8.8",
        "tls://8.8.4.4",
        "tls://9.9.9.9",
        "tls://149.112.112.112",
        "tls://94.140.14.14",
        "tls://94.140.15.15",
        "tls://194.242.2.2",
        "tls://194.242.2.3",
    ]
)

DEFAULT_DOQ = _dedupe(
    [
        "quic://dns.adguard.com",
        "quic://dns.google",
        "quic://dns.cloudflare-dns.com",
    ]
)


def build_singbox_dns_profile() -> Dict[str, Any]:
    servers: List[Dict[str, Any]] = []

    for idx, address in enumerate(DEFAULT_DOH):
        servers.append(
            {
                "tag": f"doh-{idx}",
                "address": address,
                "detour": "direct",
            }
        )

    for idx, address in enumerate(DEFAULT_DOT):
        servers.append(
            {
                "tag": f"dot-{idx}",
                "address": address,
                "detour": "direct",
            }
        )

    for idx, address in enumerate(DEFAULT_DOQ):
        servers.append(
            {
                "tag": f"doq-{idx}",
                "address": address,
                "detour": "direct",
            }
        )

    servers.append({"tag": "local", "address": "local", "detour": "direct"})

    return {
        "servers": servers,
        "strategy": "prefer_ipv4",
        "independent_cache": True,
        "final": "doh-0",
    }


def build_clash_dns_profile() -> Dict[str, Any]:
    nameserver = _dedupe(DEFAULT_DOH + DEFAULT_DOT + DEFAULT_DOQ)
    fallback = _dedupe(
        [
            "https://dns.quad9.net/dns-query",
            "https://cloudflare-dns.com/dns-query",
            "tls://9.9.9.9",
            "tls://1.1.1.1",
        ]
    )

    return {
        "enable": True,
        "listen": "0.0.0.0:1053",
        "enhanced-mode": "redir-host",
        "use-hosts": True,
        "nameserver": nameserver,
        "fallback": fallback,
        "fallback-filter": {
            "geoip": False,
            "ipcidr": ["0.0.0.0/0"],
        },
    }
