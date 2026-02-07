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

DEFAULT_FALLBACK = _dedupe(
    [
        "https://dns.quad9.net/dns-query",
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/dns-query",
        "tls://9.9.9.9",
        "tls://1.1.1.1",
    ]
)

# Iranian Infrastructure DNS (Intranet/National Network)
# These servers often respond from inside Iran even when international DNS is blocked.
IRAN_INFRASTRUCTURE_DNS = {
    # DCI Infrastructure - Tehran (LCT EMAM)
    "217.218.127.104": "DCI Tehran",
    "217.218.127.105": "DCI Tehran",
    "217.218.127.106": "DCI Tehran",
    "217.218.155.105": "DCI Tehran",
    "217.218.155.106": "DCI Tehran",
    "217.218.127.127": "Tehran - Telecommunication Infra",
    "217.218.155.155": "Tehran - Telecommunication Infra",

    # DCI Infrastructure - Other cities
    "217.219.0.104": "DCI Esfahan",
    "217.219.96.104": "DCI Shiraz",
    "217.219.192.104": "DCI Hamedan",
    "217.219.128.104": "DCI Tabriz",
    "217.219.224.104": "DCI Ahvaz",
    "217.219.64.104": "DCI Mashhad",
    "217.219.160.104": "DCI Babol",

    # Key ISP DNS
    "80.191.233.17": "Tehran - Iran Telecom",
    "217.219.72.194": "West Azerbaijan - Iran Telecom",
    "2.185.239.133": "West Azerbaijan - Iran Telecom",
    "217.219.132.88": "East Azerbaijan - Iran Telecom",
    "185.109.74.85": "Bushehr - Pishgaman",
    "217.219.250.200": "Fars - Iran Telecom",
    "89.144.144.144": "Gilan - Andishe Sabz",
    "5.200.200.200": "Golestan - Iran Telecom",
    "185.186.242.161": "Isfahan - Gostaresh",
    "78.39.101.186": "Kerman - Iran Telecom",
    "185.23.131.73": "Khorasan-e Razavi - Razavi ICT",
    "37.156.29.27": "Khorasan-e Razavi - Mobin Net",
    "31.47.37.35": "Mazandaran - Afranet",
    "80.75.5.100": "Mazandaran - Afranet",
    "217.218.234.221": "Qazvin - Iran Telecom",
    "78.38.122.12": "South Khorasan - Iran Telecom",
    "94.183.42.232": "Aria Shatel",
    "178.22.122.100": "Asiatech",
    "185.98.113.113": "Asiatech",
    "213.176.123.5": "Iranian Research Org",
    "194.225.62.80": "Tehran University",
    "92.42.49.43": "Iran Cell",
    "2.188.21.50": "Respina/Infra (Internal)",
    "2.188.21.46": "Respina/Infra (Internal)",
    "2.188.21.130": "Respina/Infra (Internal)",
    "217.218.52.5": "Infra (Internal)",
}

# Special Cloudflare IPs reported to work better
CLOUDFLARE_OPTIMIZED_IPS = [
    "108.162.192.0",
    "162.159.38.0",
    "162.159.44.0",
    "172.64.32.0",
    "34.153.65.94",
    "34.153.64.86",
    "34.153.65.92",
    "208.103.161.11",
    "208.103.161.3",
    "208.103.161.9",
    "208.103.161.45",
    "208.103.161.62",
    "208.103.161.172",
    "208.103.161.103",
    "208.103.161.138",
    "208.103.161.121",
    "208.103.161.6",
]

# Zeus DNS (Anti-Censorship)
ZEUS_DNS = ["37.32.5.60", "37.32.5.61"]


def build_resolver_sets() -> tuple[list[str], list[str]]:
    primary = _dedupe(DEFAULT_DOH + DEFAULT_DOT + DEFAULT_DOQ)
    fallback = _dedupe(DEFAULT_FALLBACK)
    return primary, fallback


def build_singbox_dns_profile() -> Dict[str, Any]:
    """
    Returns a robust DNS configuration matching the V2RayN example format.
    Updated with intelligence data (IR/CF IPs).
    """
    SELECTOR_TAG = "🌍 Proxy Select"

    # Merge optimized IPs into Cloudflare definition
    cf_ips = [
        "104.16.249.249", "104.16.248.249", "2606:4700::6810:f8f9", "2606:4700::6810:f9f9"
    ] + CLOUDFLARE_OPTIMIZED_IPS[:4]  # Add top 4 optimized IPs

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
                    "cloudflare-dns.com": cf_ips,
                    "zeus-dns": ZEUS_DNS
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
