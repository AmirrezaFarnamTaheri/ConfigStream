# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from .constants import PROTOCOL_COLORS


class AppSettings(BaseSettings):
    """Centralized configuration for all proxy operations"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Allow extra env vars
    )

    # Test URLs and timeouts
    TEST_URLS: dict[str, str] = {
        "google": "https://www.google.com/generate_204",
        "cloudflare": "https://www.cloudflare.com/cdn-cgi/trace",
        "gstatic": "https://www.gstatic.com/generate_204",
        "firefox": "http://detectportal.firefox.com/success.txt",
        "httpbin": "https://httpbin.org/status/200",
        "amazon": "https://www.amazon.com/robots.txt",
        "microsoft": "https://www.microsoft.com/robots.txt",
        "apple": "https://www.apple.com/robots.txt",
    }

    TEST_TIMEOUT: int = 15
    FETCH_TIMEOUT: int = 15
    SECURITY_CHECK_TIMEOUT: int = 8
    RETEST_TIMEOUT: int = 6
    GEOIP_TIMEOUT: int = 5
    # Soft time limit for a batch run (0 disables). Default ~5.5 hours.
    BATCH_TIME_LIMIT_SECONDS: int = 20000
    # Grace period after soft stop before hard cancellation.
    BATCH_TIME_LIMIT_GRACE_SECONDS: int = 900
    GEOIP_CITY_DB_PATH: str = "data/GeoLite2-City.mmdb"
    GEOIP_ASN_DB_PATH: str = "data/GeoLite2-ASN.mmdb"

    # Latency thresholds
    MIN_LATENCY: int = 10
    MAX_LATENCY: int = 10000
    LAT_CONNECT_TIMEOUT_MS: int = 3500
    LAT_HTTP_TIMEOUT_MS: int = 3500
    LAT_PER_PROXY_BUDGET_MS: int = 6000
    LAT_SOFT_CAP_MS: int = 1800

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # [PHASE 2] Producer Concurrency
    PRODUCER_MAX_CONCURRENCY: int = 100

    # Tester Concurrency Limits
    GO_TESTER_BATCH_SIZE: int = 0
    PY_TESTER_BATCH_SIZE: int = 0

    # Intelligence Layer
    WARP_KEY_POOL: str = "[]"
    INTRANET_ORIGIN: str = "IR"
    OPTIMAL_RELAY_ORIGIN: str = "IR"
    WARP_PEER_KEY: Optional[str] = None  # Added for washer/core.py

    # Memory management
    BATCH_SIZE: int = 50
    MAX_SEEN_KEYS: int = 0
    CACHE_TTL: int = 1800
    MAX_WORKERS: int = 0

    # Scoring weights
    SCORE_WEIGHTS: dict[str, float] = {
        "historical_success": 40.0,
        "latency": 30.0,
        "security": 20.0,
        "current_status": 10.0,
    }

    # Protocol colors (Not loaded from env, but kept for compat)
    PROTOCOL_COLORS: dict[str, str] = PROTOCOL_COLORS

    # Security
    BLOCKED_COUNTRIES: str = ""

    # Malicious node detection
    # Pydantic doesn't easily map nested dicts with defaults from env unless using JSON
    # We'll define the complex dict as a property or field with default factory
    # For now, we keep it as a class attribute since it's rarely env-overridden in detail
    SECURITY: dict = {
        "content_injection_threshold": 5,
        "header_strip_threshold": 2,
        "redirect_follow_limit": 3,
        "suspicious_port_range": [(0, 1024), (5000, 5999), (8000, 8999)],
        "malicious_asn_list": [],
    }

    # Logging
    MASK_SENSITIVE_DATA: bool = True
    LOG_LEVEL: str = "INFO"
    CANARY_URL: str = ""

    # Feature flags
    DNS_CACHE_ENABLED: bool = True
    CIRCUIT_BREAKER_ENABLED: bool = True
    HEDGING_ENABLED: bool = True
    AIMD_ENABLED: bool = True
    AIMD_P50_MS: int = 400
    AIMD_P95_MS: int = 1500
    PER_HOST_MAX_CONCURRENCY: int = 32
    HEDGE_AFTER_MS: int = 800
    HEDGE_MAX_EXTRA: int = 1
    CIRCUIT_TRIP_CONN_ERRORS: int = 5
    CIRCUIT_TRIP_5XX_RATE: float = 0.2
    CIRCUIT_OPEN_SEC: int = 120
    QUEUE_MAX_TRIES: int = 5
    TLS_TESTS_ENABLED: bool = True

    # Optional pipeline toggles (default to enabled)
    ENABLE_CACHE_WARMING: bool = True
    ENABLE_SMART_CHAINING: bool = True
    ENABLE_ANOMALY_DETECTION: bool = True

    # Strict tester security mode (honeypot + extra checks)
    STRICT_SECURITY: bool = False

    # Proxy renaming
    RENAME_TEMPLATE: Optional[str] = None

    # Update Interval
    UPDATE_INTERVAL_HOURS: int = 5

    # Security Validator
    ALLOW_PRIVATE_IPS: bool = True
    INCLUDE_INSECURE_PROXIES: bool = True

    # Shuffle
    CONFIGSTREAM_SHUFFLE_SEED: Optional[str] = None

    # Secrets (Optional)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    VT_API_KEY: Optional[str] = None
    ADMIN_API_KEY: Optional[str] = None
    STEGO_KEY: Optional[str] = None
    CONFIG_STREAM_KEY: Optional[str] = None
    MAXMIND_LICENSE_KEY: Optional[str] = None

    # Binary Paths
    CONFIGSTREAM_TESTER_BIN: Optional[str] = None
    SS_LIB_SHA256: Optional[str] = None

    # Flags
    USE_VWARP_TUNNEL: bool = True
    FORCE_SCANNER: bool = False
    ALLOW_ACTIVE_SCANNING: bool = False

    # Deduplication behavior
    DEDUP_IGNORE_PROTOCOL: bool = False
    ENABLE_ENDPOINT_FILTERING: bool = True

    # Server Config
    FRONTEND_DIR: Optional[str] = None
    ALLOWED_ORIGINS: str = (
        "http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000"
    )
    ALLOWED_ORIGIN_REGEX: str = r"https://.*\.github\.io"
    ENVIRONMENT: str = "production"

    # Fetcher
    MAX_RESPONSE_SIZE: int = 0
    QUALITY_DB_PATH: str = "data/source_quality.db"

    # Score Tuning (Advanced)
    SCORE_SIGMOID_CENTER_RATIO: float = 0.6
    SCORE_SIGMOID_SLOPE_RATIO: float = 0.2

    def model_post_init(self, __context):
        """Update nested security settings from env vars if needed."""
        # Create a copy to avoid modifying the class attribute for all instances
        self.SECURITY = self.SECURITY.copy()
        if self.BLOCKED_COUNTRIES:
            self.SECURITY["blocked_countries"] = self.BLOCKED_COUNTRIES.split(",")
        else:
            self.SECURITY["blocked_countries"] = []

    def validate_settings(self) -> None:
        """Validate configuration settings."""
        if self.TEST_TIMEOUT <= 0:
            raise ValueError("TEST_TIMEOUT must be positive")
        if self.FETCH_TIMEOUT <= 0:
            raise ValueError("FETCH_TIMEOUT must be positive")
        if self.BATCH_TIME_LIMIT_SECONDS < 0:
            raise ValueError("BATCH_TIME_LIMIT_SECONDS must be >= 0")
        if self.BATCH_TIME_LIMIT_GRACE_SECONDS < 0:
            raise ValueError("BATCH_TIME_LIMIT_GRACE_SECONDS must be >= 0")
        if self.MAX_WORKERS < 0:
            raise ValueError("MAX_WORKERS must be >= 0")
        if self.BATCH_SIZE <= 0:
            raise ValueError("BATCH_SIZE must be > 0")
        if self.RATE_LIMIT_REQUESTS <= 0:
            raise ValueError("RATE_LIMIT_REQUESTS must be positive")
