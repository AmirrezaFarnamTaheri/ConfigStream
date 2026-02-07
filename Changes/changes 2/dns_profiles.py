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

IR_DNS = _dedupe(
    [
        "217.218.52.5",
        "108.162.192.0",
        "162.159.38.0",
        "217.218.26.74",
        "162.159.44.0",
        "172.64.32.0",
        "2.188.21.46",
        "34.153.65.94",
        "34.153.64.86",
        "34.153.65.92",
        "37.32.5.60",  # Zeus Preferred
        "37.32.5.61",  # Zeus Alternate
        "2.188.21.130",  # Infrastructure
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
    Returns a robust DNS configuration matching the V2RayN example format.
    """
    SELECTOR_TAG = "🌍 Proxy Select"

    return {
        "servers": [
            {
                "server": "223.5.5.5",
                "type": "udp",
                "tag": "local_local",
                "detour": "direct",
            },
            {
                "server": "cloudflare-dns.com",
                "domain_resolver": "hosts_dns",
                "path": "/dns-query",
                "type": "https",
                "tag": "remote_dns",
                "detour": SELECTOR_TAG
            },
            {
                "server": "dns.alidns.com",
                "domain_resolver": "hosts_dns",
                "path": "/dns-query",
                "type": "https",
                "tag": "direct_dns",
                "detour": "direct"
            },
            {
                "predefined": {
                    "dns.google": [
                        "8.8.8.8", "8.8.4.4", "2001:4860:4860::8888", "2001:4860:4860::8844"
                    ],
                    "dns.alidns.com": [
                        "223.5.5.5", "223.6.6.6", "2400:3200::1", "2400:3200:baba::1"
                    ],
                    "one.one.one.one": [
                        "1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"
                    ],
                    "cloudflare-dns.com": [
                        "104.16.249.249", "104.16.248.249", "2606:4700::6810:f8f9", "2606:4700::6810:f9f9"
                    ]
                },
                "type": "hosts",
                "tag": "hosts_dns"
            },
            {
                "server": "dns.alidns.com",
                "domain_resolver": "hosts_dns",
                "path": "/dns-query",
                "type": "https",
                "tag": "ech_dns"
            }
        ],
        "rules": [
            {
                "server": "local_local",
                "domain": ["sing_box-ProxyChain"]
            },
            {
                "server": "hosts_dns",
                "ip_accept_any": True
            },
            {
                "server": "remote_dns",
                "clash_mode": "Global"
            },
            {
                "server": "direct_dns",
                "clash_mode": "Direct"
            },
            {
                "action": "predefined",
                "rcode": "NOTIMP",
                "query_type": [64, 65]
            },
            {
                "rule_set": ["geosite-category-ads-all"],
                "action": "predefined",
                "rcode": "NXDOMAIN"
            },
            {
                "server": "direct_dns",
                "rule_set": ["geosite-private", "geosite-ir"]
            }
        ],
        "final": "remote_dns",
        "independent_cache": True
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
