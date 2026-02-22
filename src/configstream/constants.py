# SPDX-License-Identifier: AGPL-3.0-or-later
"""Centralized constants for all modules."""

import os


# Network & Tunnel Configuration
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


VWARP_SOCKS5_PORT = _env_int(
    "VWARP_SOCKS5_PORT", 10808
)  # Default port for Vwarp SOCKS5 tunnel
VWARP_BIND_ADDRESS = "127.0.0.1"  # Localhost binding for security

# Anomaly Detection Constants
Z_SCORE_NORMAL_CONSTANT = 0.6745  # Modified Z-score constant (0.6745 ≈ 0.75 * IQR)

# Cache Warming Thresholds
CACHE_WARMING_HIGH_SCORE_THRESHOLD = 1000  # Proxy count for high-score tier
CACHE_WARMING_MID_SCORE_THRESHOLD = 100  # Proxy count for mid-score tier
CACHE_WARMING_LOW_SCORE_THRESHOLD = 50  # Proxy count for low-score tier

# VirusTotal Cache Size
VIRUSTOTAL_CACHE_SIZE = 1000  # LRU cache size for VT lookups

# Size Limits (0 = unlimited; use streaming for large sources.)
MAX_B64_INPUT_SIZE = _env_int("MAX_B64_INPUT_SIZE", 0)
MAX_B64_OUTPUT_SIZE = _env_int("MAX_B64_OUTPUT_SIZE", 0)
MAX_CONFIG_LINE_LENGTH = _env_int("MAX_CONFIG_LINE_LENGTH", 0)  # 0 = unlimited
MAX_LINES_PER_SOURCE = _env_int("MAX_LINES_PER_SOURCE", 0)  # 0 = unlimited
MAX_OPENVPN_CONFIG_SIZE = _env_int("MAX_OPENVPN_CONFIG_SIZE", 0)

# Ports & Domains
# Removed 3306 (MySQL), 5432 (Postgres), 6379 (Redis), 27017 (Mongo)
# These are commonly used for tunneling.
# Kept truly dangerous admin/cleartext ports (FTP, SSH, Telnet, SMB).
DANGEROUS_PORTS = [21, 22, 23, 25, 110, 143, 445, 3389]

# Private IP ranges that should NOT be accessed via public proxies
SUSPICIOUS_DOMAINS = [
    "localhost",
    "127.",  # Loopback
    "127.0.0.1",  # Zero
    "10.",  # Private Class A
    "192.168.",  # Private Class C
    "169.254.",  # Link-local
    "100.64.",  # Carrier Grade NAT
    # Class B Private: 172.16.0.0 - 172.31.255.255
    # Regex matching would be better, but prefix list covers most
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "fc00:",
    "fd00:",  # IPv6 ULA
]

MAX_PORT = 65535

# Protocols
VALID_PROTOCOLS = [
    "vmess",
    "vless",
    "shadowsocks",
    "ss",
    "ss2022",
    "ssr",
    "trojan",
    "hysteria",
    "hysteria2",
    "hy2",
    "husi",  # Hysteria2/Sing-box URI scheme used in the wild
    "tuic",
    "wireguard",
    "wg",
    "exclave",
    "naive",
    "naive+https",  # Naive proxy with HTTPS
    "naive+http",  # Naive proxy with HTTP
    "snell",
    "brook",
    "juicity",
    "xray",
    "xtls",
    "v2ray",  # V2Ray JSON configs
    "ssh",
    "http",
    "https",
    "socks",
    "socks4",
    "socks5",
    "anytls",
]

# Canonical protocol ordering for user-facing output artifacts.
# Keeps high-demand censorship-evasion transports first while preserving
# deterministic ordering across base64/proxies/adapters/chosen files.
OUTPUT_PROTOCOL_ORDER = [
    "hysteria2",
    "hysteria",
    "tuic",
    "wireguard",
    "vmess",
    "vless",
    "trojan",
    "shadowsocks",
    "ss2022",
    "ssr",
    "socks5",
    "socks4",
    "http",
    "https",
    "ssh",
    "naive",
    "anytls",
    "snell",
    "brook",
    "juicity",
    "xray",
    "xtls",
    "v2ray",
    "exclave",
    "openvpn",
    "revived",
    "unknown",
]

_OUTPUT_PROTOCOL_ALIASES = {
    "ss": "shadowsocks",
    "wg": "wireguard",
    "hy2": "hysteria2",
    "husi": "hysteria2",
    "socks": "socks5",
}

_OUTPUT_PROTOCOL_ORDER_INDEX = {
    proto: idx for idx, proto in enumerate(OUTPUT_PROTOCOL_ORDER)
}


def canonical_protocol_name(protocol: str) -> str:
    """Normalize protocol aliases for consistent output grouping/sorting."""
    normalized = (protocol or "").strip().lower()
    if not normalized:
        return "unknown"
    return _OUTPUT_PROTOCOL_ALIASES.get(normalized, normalized)


def protocol_sort_key(protocol: str) -> tuple[int, str]:
    """Stable protocol sort key: preferred order, then lexical fallback."""
    canonical = canonical_protocol_name(protocol)
    return (
        _OUTPUT_PROTOCOL_ORDER_INDEX.get(canonical, len(OUTPUT_PROTOCOL_ORDER)),
        canonical,
    )


# Selection criteria for "chosen" proxies
CHOSEN_TOP_PER_PROTOCOL = 40  # Top N proxies per protocol
CHOSEN_TOTAL_TARGET = 1000  # Total target for chosen list

# Domains that are typically subscription sources and should not be treated as proxy content
BLOCKED_DOMAINS = [
    "github.com",
    "githubusercontent.com",
    "raw.githubusercontent.com",
    "gitlab.com",
    "bitbucket.org",
    "t.me",
    "telegram",
    "pastebin",
    ".workers.dev",
    "netlify.app",
    "vercel.app",
    "pages.dev",
    "cloudflare.com",
    "jsdelivr.net",
    "fastgit.org",
    "herokuapp.com",
    "render.com",
    "onrender.com",
    "hf.space",
    "huggingface.co",
]

# Latency Buckets (ms)
LATENCY_FAST = 200
LATENCY_MEDIUM = 800
LATENCY_SLOW = 2000
