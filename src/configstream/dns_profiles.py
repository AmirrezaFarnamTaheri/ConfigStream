# SPDX-License-Identifier: AGPL-3.0-or-later
"""
DNS resolver profiles for Sing-box and Clash output configurations.
Imports intelligence data from the single source of truth in dns_lists.py.
"""

from __future__ import annotations

from typing import Dict, Any, List

from .intelligence.dns_lists import (
    CLOUDFLARE_OPTIMIZED_IPS as CLOUDFLARE_OPTIMIZED_IPS,
    IRAN_INFRASTRUCTURE_DNS as IRAN_INFRASTRUCTURE_DNS,
)

__all__ = [
    "CLOUDFLARE_OPTIMIZED_IPS",
    "IRAN_INFRASTRUCTURE_DNS",
    "DEFAULT_DOH",
    "build_singbox_dns_profile",
    "build_clash_dns_profile",
    "build_resolver_sets",
]


def _dedupe(items: List[str]) -> List[str]:
    seen: set[str] = set()
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
        # Note: Cloudflare DoQ removed — CF does not offer public DoQ service
    ]
)

DEFAULT_FALLBACK = _dedupe(
    [
        "https://dns.quad9.net/dns-query",
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/dns-query",
        "tls://9.9.9.9",
        "tls://1.1.1.1",
    ]
)


def build_resolver_sets() -> tuple[list[str], list[str]]:
    primary = _dedupe(DEFAULT_DOH + DEFAULT_DOT + DEFAULT_DOQ)
    fallback = _dedupe(DEFAULT_FALLBACK)
    return primary, fallback


def build_singbox_dns_profile() -> Dict[str, Any]:
    """Return a native Sing-box 1.12+ DNS profile.

    Hostname-based DNS servers explicitly resolve through ``local_local`` so
    native validation does not rely on the removed implicit resolver behavior.
    """

    return {
        "servers": [
            {
                "type": "https",
                "tag": "remote_dns",
                "server": "cloudflare-dns.com",
                "server_port": 443,
                "path": "/dns-query",
                "domain_resolver": "local_local",
            },
            {
                "type": "https",
                "tag": "direct_dns",
                "server": "dns.google",
                "server_port": 443,
                "path": "/dns-query",
                "domain_resolver": "local_local",
                "detour": "direct",
            },
            {
                "type": "udp",
                "tag": "local_local",
                "server": "1.1.1.1",
                "server_port": 53,
                "detour": "direct",
            },
        ],
        "rules": [
            {
                "domain": ["sing_box-ProxyChain"],
                "action": "route",
                "server": "local_local",
            },
            {
                "clash_mode": "Global",
                "action": "route",
                "server": "remote_dns",
            },
            {
                "clash_mode": "Direct",
                "action": "route",
                "server": "direct_dns",
            },
            {
                "rule_set": ["geosite-category-ads-all"],
                "action": "predefined",
                "rcode": "NOERROR",
            },
            {
                "rule_set": ["geosite-private", "geosite-ir"],
                "action": "route",
                "server": "direct_dns",
            },
        ],
        "final": "remote_dns",
    }


def build_clash_dns_profile() -> Dict[str, Any]:
    nameserver = _dedupe(DEFAULT_DOH + DEFAULT_DOT + DEFAULT_DOQ)
    fallback = _dedupe(DEFAULT_FALLBACK)

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
