import os
from dataclasses import dataclass


@dataclass
class AppSettings:
    """Centralized configuration for all proxy operations"""

    # Test URLs and timeouts (CENTRALIZED)
    TEST_URLS = {
        "google": "https://www.google.com/generate_204",
        "cloudflare": "https://www.cloudflare.com/cdn-cgi/trace",
        "gstatic": "https://www.gstatic.com/generate_204",
        "firefox": "http://detectportal.firefox.com/success.txt",
        "httpbin": "https://httpbin.org/status/200",
        "amazon": "https://www.amazon.com/robots.txt",
        "microsoft": "https://www.microsoft.com/robots.txt",
        "apple": "https://www.apple.com/robots.txt",
    }

    TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "6"))  # Reduced from 10 to 6 for faster testing
    SECURITY_CHECK_TIMEOUT = int(os.getenv("SECURITY_CHECK_TIMEOUT", "8"))
    RETEST_TIMEOUT = int(os.getenv("RETEST_TIMEOUT", "6"))  # Reduced from 8 to 6
    GEOIP_TIMEOUT = int(os.getenv("GEOIP_TIMEOUT", "5"))

    # Latency thresholds
    MIN_LATENCY = int(os.getenv("MIN_LATENCY", "10"))  # milliseconds
    MAX_LATENCY = int(os.getenv("MAX_LATENCY", "10000"))  # milliseconds
    LAT_CONNECT_TIMEOUT_MS = int(os.getenv("LAT_CONNECT_TIMEOUT_MS", "3500"))
    LAT_HTTP_TIMEOUT_MS = int(os.getenv("LAT_HTTP_TIMEOUT_MS", "3500"))
    LAT_PER_PROXY_BUDGET_MS = int(os.getenv("LAT_PER_PROXY_BUDGET_MS", "6000"))
    LAT_SOFT_CAP_MS = int(os.getenv("LAT_SOFT_CAP_MS", "1800"))

    # Rate limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

    # Memory management
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
    CACHE_TTL = int(os.getenv("CACHE_TTL", "1800"))  # 30 minutes

    # Protocol colors (moved from hardcoded JavaScript)
    PROTOCOL_COLORS = {
        "vmess": "#FF6B6B",
        "vless": "#4ECDC4",
        "shadowsocks": "#45B7D1",
        "trojan": "#96CEB4",
        "hysteria": "#FFEAA7",
        "hysteria2": "#DFE6E9",
        "tuic": "#A29BFE",
        "wireguard": "#74B9FF",
        "naive": "#FD79A8",
        "http": "#FDCB6E",
        "https": "#6C5CE7",
        "socks": "#00B894",
    }

    # Malicious node detection thresholds
    SECURITY = {
        "content_injection_threshold": 5,  # bytes difference
        "header_strip_threshold": 2,  # headers
        "redirect_follow_limit": 3,
        "suspicious_port_range": [(0, 1024), (5000, 5999), (8000, 8999)],
        "blocked_countries": os.getenv("BLOCKED_COUNTRIES", "").split(","),
        "malicious_asn_list": [
            # Known malicious ASNs - expand as needed
            "AS13335",  # Cloudflare - some malicious uses
            "AS16509",  # Amazon - honeypot detection
        ],
    }

    # Logging
    MASK_SENSITIVE_DATA = True
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
