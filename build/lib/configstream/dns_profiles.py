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
    """
    Returns a robust DNS configuration.
    """
    SELECTOR_TAG = "🌍 Proxy Select"

    return {
        "servers": [
            {
                "address": "https://cloudflare-dns.com/dns-query",
                "address_resolver": "local_local",
                "strategy": "prefer_ipv4",
                "tag": "remote_dns",
                "detour": SELECTOR_TAG,
            },
            {
                "address": "https://dns.google/dns-query",
                "address_resolver": "local_local",
                "strategy": "prefer_ipv4",
                "tag": "direct_dns",
                "detour": "direct",
            },
            {
                "address": "rcode://success",
                "tag": "block_dns",
            },
            {
                "address": "1.1.1.1",
                "tag": "local_local",
                "detour": "direct",
            },
        ],
        "rules": [
            {
                "server": "local_local",
                "domain": ["sing_box-ProxyChain"],
            },
            {
                "server": "remote_dns",
                "clash_mode": "Global",
            },
            {
                "server": "direct_dns",
                "clash_mode": "Direct",
            },
            {
                "server": "block_dns",
                "rule_set": ["geosite-category-ads-all"],
            },
            {
                "server": "direct_dns",
                "rule_set": ["geosite-private", "geosite-ir"],
            },
        ],
        "final": "remote_dns",
        "independent_cache": True,
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
