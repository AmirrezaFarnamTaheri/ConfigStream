"""Centralized constants for all modules."""

# Size Limits
MAX_B64_INPUT_SIZE = 10 * 1024 * 1024  # 10 MB (Audit Recommendation: Reduced from 50MB)
MAX_B64_OUTPUT_SIZE = (
    50 * 1024 * 1024
)  # 50 MB (Audit Recommendation: Reduced from 100MB)
MAX_CONFIG_LINE_LENGTH = 10000
MAX_LINES_PER_SOURCE = 20000  # Reduced from 40000 to improve memory safety
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

# Protocol colors for UI/frontend
PROTOCOL_COLORS = {
    "vmess": "#FF6B6B",
    "vless": "#4ECDC4",
    "shadowsocks": "#45B7D1",
    "ss": "#45B7D1",  # Alias for shadowsocks
    "trojan": "#96CEB4",
    "hysteria": "#FFEAA7",
    "hysteria2": "#DFE6E9",
    "hy2": "#DFE6E9",  # Alias for hysteria2
    "tuic": "#A29BFE",
    "wireguard": "#74B9FF",
    "wg": "#74B9FF",  # Alias for wireguard
    "naive": "#FD79A8",
    "http": "#FDCB6E",
    "https": "#6C5CE7",
    "socks": "#00B894",
    "socks4": "#00B894",
    "socks5": "#00B894",
    "openvpn": "#E84393",
}

# Domains that are typically subscription sources and should not be treated as proxy content
BLOCKED_DOMAINS = [
    "github.com",
    "githubusercontent.com",
    "githubrowcontent.com",
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
