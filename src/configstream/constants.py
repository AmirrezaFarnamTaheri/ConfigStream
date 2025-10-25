"""Centralized constants for all modules."""

# Size Limits
MAX_B64_INPUT_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_B64_OUTPUT_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_CONFIG_LINE_LENGTH = 10000
MAX_LINES_PER_SOURCE = 10000
MAX_SOURCE_URL_LENGTH = 2048

# Timeouts (seconds)
FETCH_TIMEOUT = 30
TEST_TIMEOUT = 10
GEOIP_TIMEOUT = 5

# Ports & Domains
DANGEROUS_PORTS = [21, 22, 23, 25, 110, 143, 445, 3306, 3389, 5432, 6379, 27017]
SUSPICIOUS_DOMAINS = ["localhost", "127.0.0.1", "0.0.0.0", "169.254.", "192.168.", "10."]
MIN_SAFE_PORT = 1024
MAX_PORT = 65535

# Protocols
VALID_PROTOCOLS = [
    "vmess",
    "vless",
    "shadowsocks",
    "ss",
    "ssr",
    "trojan",
    "hysteria",
    "hysteria2",
    "hy2",
    "tuic",
    "wireguard",
    "wg",
    "naive",
    "snell",
    "brook",
    "juicity",
    "http",
    "https",
    "socks",
    "socks4",
    "socks5",
]

# Test URLs for proxy validation (centralized configuration)
TEST_URLS = {
    "google": "https://www.google.com/generate_204",
    "cloudflare": "https://www.cloudflare.com/cdn-cgi/trace",
    "gstatic": "https://www.gstatic.com/generate_204",
    "firefox": "http://detectportal.firefox.com/success.txt",
    "httpbin": "https://httpbin.org/status/200",
    "amazon": "https://www.amazon.com/robots.txt",
    "bing": "https://www.bing.com/robots.txt",
    "github": "https://api.github.com",
}

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
