import os
from typing import Optional, List, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from .constants import PROTOCOL_COLORS


class AppSettings(BaseSettings):
    """Centralized configuration for all proxy operations"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Test URLs and timeouts (CENTRALIZED)
    TEST_URLS: Dict[str, str] = {
        "google": "https://www.google.com/generate_204",
        "cloudflare": "https://www.cloudflare.com/cdn-cgi/trace",
        "gstatic": "https://www.gstatic.com/generate_204",
        "firefox": "http://detectportal.firefox.com/success.txt",
        "httpbin": "https://httpbin.org/status/200",
        "amazon": "https://www.amazon.com/robots.txt",
        "microsoft": "https://www.microsoft.com/robots.txt",
        "apple": "https://www.apple.com/robots.txt",
    }

    TEST_TIMEOUT: int = Field(default=15, gt=0)
    FETCH_TIMEOUT: int = Field(default=15, gt=0)
    SECURITY_CHECK_TIMEOUT: int = Field(default=8, gt=0)
    RETEST_TIMEOUT: int = Field(default=6, gt=0)
    GEOIP_TIMEOUT: int = Field(default=5, gt=0)

    # Latency thresholds (milliseconds)
    MIN_LATENCY: int = 10
    MAX_LATENCY: int = 10000
    LAT_CONNECT_TIMEOUT_MS: int = 3500
    LAT_HTTP_TIMEOUT_MS: int = 3500
    LAT_PER_PROXY_BUDGET_MS: int = 6000
    LAT_SOFT_CAP_MS: int = 1800

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, gt=0)
    RATE_LIMIT_WINDOW: int = Field(default=60, gt=0)  # seconds

    # Memory management
    BATCH_SIZE: int = Field(default=50, ge=1, le=1000)
    CACHE_TTL: int = 1800  # 30 minutes

    # Scoring weights for health calculation
    SCORE_WEIGHTS: Dict[str, float] = {
        "historical_success": 40.0,
        "latency": 30.0,
        "security": 20.0,
        "current_status": 10.0,
    }

    # Protocol colors for UI
    PROTOCOL_COLORS: Dict[str, str] = PROTOCOL_COLORS

    # Malicious node detection thresholds
    SECURITY: Dict = {
        "content_injection_threshold": 5,  # bytes difference
        "header_strip_threshold": 2,  # headers
        "redirect_follow_limit": 3,
        "suspicious_port_range": [(0, 1024), (5000, 5999), (8000, 8999)],
        "blocked_countries": os.getenv("BLOCKED_COUNTRIES", "").split(",") if os.getenv("BLOCKED_COUNTRIES") else [],
        "malicious_asn_list": [],
    }

    # Logging
    MASK_SENSITIVE_DATA: bool = True
    LOG_LEVEL: str = "INFO"
    CANARY_URL: str = "https://httpbin.org"

    # Feature flags
    DNS_CACHE_ENABLED: bool = True
    CIRCUIT_BREAKER_ENABLED: bool = True
    HEDGING_ENABLED: bool = True
    AIMD_ENABLED: bool = True
    AIMD_P50_MS: int = 400
    AIMD_P95_MS: int = 1500
    PER_HOST_MAX_CONCURRENCY: int = 32
    HEDGE_AFTER_MS: Optional[int] = 800
    HEDGE_MAX_EXTRA: int = 1
    CIRCUIT_TRIP_CONN_ERRORS: int = 5
    CIRCUIT_TRIP_5XX_RATE: float = 0.2
    CIRCUIT_OPEN_SEC: int = 120
    QUEUE_MAX_TRIES: int = 5
    TLS_TESTS_ALLOW_INSECURE: bool = False
    TLS_TESTS_ENABLED: bool = True

    # Proxy renaming/tagging template
    RENAME_TEMPLATE: Optional[str] = None

    # Security Validator Settings
    ALLOW_PRIVATE_IPS: bool = False

    # Explicit validation logic is handled by Pydantic's validators automatically
    # but we can add custom ones if needed.
