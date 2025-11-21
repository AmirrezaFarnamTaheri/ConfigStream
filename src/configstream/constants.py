"""Centralized constants for all modules."""

# Size Limits
MAX_B64_INPUT_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_B64_OUTPUT_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_CONFIG_LINE_LENGTH = 10000
MAX_LINES_PER_SOURCE = 10000
MAX_SOURCE_URL_LENGTH = 2048

# Ports & Domains
# Removed 3306 (MySQL), 5432 (Postgres), 6379 (Redis), 27017 (Mongo)
# These are commonly used for tunneling.
# Kept truly dangerous admin/cleartext ports (FTP, SSH, Telnet, SMB).
DANGEROUS_PORTS = [21, 22, 23, 25, 110, 143, 445, 3389]
SUSPICIOUS_DOMAINS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "169.254.",
    "192.168.",
    "10.",
]
MIN_SAFE_PORT = 1024
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
    "tuic",
    "wireguard",
    "wg",
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
]

# Security issue categories (standardized)
SECURITY_CATEGORIES = [
    "weak_encryption",
    "insecure_transport",
    "dangerous_port",
    "suspicious_domain",
    "invalid_certificate",
    "missing_auth",
    "configuration_error",
    "deprecated_protocol",
]

# Selection criteria for "chosen" proxies
CHOSEN_TOP_PER_PROTOCOL = 40  # Top N proxies per protocol
CHOSEN_TOTAL_TARGET = 1000  # Total target for chosen list
