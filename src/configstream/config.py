# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    # Soft time limit for a batch run (0 disables). Default 3h45m.
    # After this, stop_event fires → producer stops fetching new sources.
    BATCH_TIME_LIMIT_SECONDS: int = 14400
    # Grace period after soft stop for consumers to finish revival, then
    # output generation (DNS, chaining, washing) runs after gather completes.
    BATCH_TIME_LIMIT_GRACE_SECONDS: int = 2700
    SHUTDOWN_GRACE_SECONDS: float = 5.0
    EVENT_STREAM_FLUSH_TIMEOUT_SECONDS: float = 2.0
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

    # Producer Concurrency
    PRODUCER_MAX_CONCURRENCY: int = 100
    # Queue/backpressure controls
    QUEUE_PUT_TIMEOUT_SECONDS: float = 0.75
    QUEUE_OVERLOAD_THRESHOLD: float = 0.8
    QUEUE_OVERLOAD_KEEP_RATIO: float = 0.6
    INGEST_MICRO_CHUNK_LINES: int = 500

    # Tester Concurrency Limits
    GO_TESTER_BATCH_SIZE: int = 0
    PY_TESTER_BATCH_SIZE: int = 0

    # Intelligence Layer
    WARP_KEY_POOL: str = "[]"
    INTRANET_ORIGIN: str = "IR"
    OPTIMAL_RELAY_ORIGIN: str = "IR"
    WARP_PEER_KEY: Optional[str] = None  # Added for washer/core.py

    # Evasion Configuration
    EVASION_MODE: str = "aggressive"  # Options: "standard", "stealth", "aggressive"
    # Standard: No evasion features
    # Stealth: TLS fragmentation + uTLS only
    # Aggressive: All evasion features (uTLS, ALPN, fragmentation, multiplexing)

    # Memory management
    BATCH_SIZE: int = 50
    MAX_SEEN_KEYS: int = 0
    CACHE_TTL: int = 1800
    MAX_WORKERS: int = 0
    MAX_B64_INPUT_SIZE: int = 0
    MAX_B64_OUTPUT_SIZE: int = 0
    MAX_CONFIG_LINE_LENGTH: int = 0
    MAX_LINES_PER_SOURCE: int = 0
    MAX_OPENVPN_CONFIG_SIZE: int = 0

    # Scoring weights
    SCORE_WEIGHTS: dict[str, float] = {
        "historical_success": 40.0,
        "latency": 30.0,
        "security": 20.0,
        "current_status": 10.0,
    }

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
    DNS_SAFE_OUTPUTS: bool = True
    DNS_HARDENED_OUTPUTS: bool = True
    # Fail the pipeline (exit non-zero) when 0 working proxies were found.
    # Outputs are still generated before final status is returned.
    FAIL_ON_ZERO_WORKING: bool = True
    DNS_SAFE_RESOLVE_TIMEOUT: float = 4.0
    DNS_SAFE_RESOLVE_BATCH: int = 500
    DNS_SAFE_RESOLVE_LIMIT: int = 0
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
    UPDATE_INTERVAL_HOURS: int = 4
    BATCH_NUMBER: str = ""

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
    VWARP_SOCKS5_PORT: int = 10808
    VWARP_BIND_ADDRESS: str = "127.0.0.1"
    VWARP_MASQUE_ENABLED: bool = True  # Enable Masque by default
    PSIPHON_ENABLED: bool = False
    PSIPHON_COUNTRY: str = "US"
    FORCE_SCANNER: bool = False
    ALLOW_ACTIVE_SCANNING: bool = False

    # Deduplication behavior
    DEDUP_IGNORE_PROTOCOL: bool = False
    ENABLE_ENDPOINT_FILTERING: bool = True
    SEEN_BLOOM_ENABLED: bool = True
    SEEN_BLOOM_EXPECTED_ITEMS: int = 2000000
    SEEN_BLOOM_FALSE_POSITIVE_RATE: float = 0.001

    # Server Config
    FRONTEND_DIR: Optional[str] = None
    ALLOWED_ORIGINS: str = (
        "http://localhost:8000,http://localhost:3000,http://127.0.0.1:8000"
    )
    ALLOWED_ORIGIN_REGEX: str = ""
    CORS_ALLOW_CREDENTIALS: bool = False
    WS_MAX_CONNECTIONS: int = 100
    WS_IDLE_TIMEOUT_SECONDS: float = 60.0
    WS_SEND_TIMEOUT_SECONDS: float = 5.0
    LAB_LIVE_TEST_ENABLED: bool = False
    LAB_TEST_TIMEOUT_SECONDS: float = 15.0
    LAB_MAX_CONFIG_BYTES: int = 65536
    ENVIRONMENT: str = "production"

    # Fetcher
    MAX_RESPONSE_SIZE: int = 0
    FETCH_MAX_REDIRECTS: int = 5
    FETCH_BLOCK_PRIVATE_NETWORKS: bool = True
    FETCH_VALIDATE_DNS: bool = True
    QUALITY_DB_PATH: str = "data/source_quality.db"
    SOURCE_PROBATION_FAILURES: int = 3
    SOURCE_DEAD_FAILURES: int = 10

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
        if self.SHUTDOWN_GRACE_SECONDS <= 0:
            raise ValueError("SHUTDOWN_GRACE_SECONDS must be > 0")
        if self.EVENT_STREAM_FLUSH_TIMEOUT_SECONDS <= 0:
            raise ValueError("EVENT_STREAM_FLUSH_TIMEOUT_SECONDS must be > 0")
        if self.MAX_WORKERS < 0:
            raise ValueError("MAX_WORKERS must be >= 0")
        if self.BATCH_SIZE <= 0:
            raise ValueError("BATCH_SIZE must be > 0")
        if self.INGEST_MICRO_CHUNK_LINES <= 0:
            raise ValueError("INGEST_MICRO_CHUNK_LINES must be > 0")
        if self.QUEUE_PUT_TIMEOUT_SECONDS <= 0:
            raise ValueError("QUEUE_PUT_TIMEOUT_SECONDS must be > 0")
        if not 0 < self.QUEUE_OVERLOAD_THRESHOLD <= 1:
            raise ValueError("QUEUE_OVERLOAD_THRESHOLD must be in (0, 1]")
        if not 0 < self.QUEUE_OVERLOAD_KEEP_RATIO <= 1:
            raise ValueError("QUEUE_OVERLOAD_KEEP_RATIO must be in (0, 1]")
        if self.SEEN_BLOOM_EXPECTED_ITEMS <= 0:
            raise ValueError("SEEN_BLOOM_EXPECTED_ITEMS must be > 0")
        if not 0 < self.SEEN_BLOOM_FALSE_POSITIVE_RATE < 1:
            raise ValueError("SEEN_BLOOM_FALSE_POSITIVE_RATE must be in (0, 1)")
        if self.RATE_LIMIT_REQUESTS <= 0:
            raise ValueError("RATE_LIMIT_REQUESTS must be positive")
        if self.SOURCE_PROBATION_FAILURES <= 0:
            raise ValueError("SOURCE_PROBATION_FAILURES must be positive")
        if self.SOURCE_DEAD_FAILURES < self.SOURCE_PROBATION_FAILURES:
            raise ValueError(
                "SOURCE_DEAD_FAILURES must be >= SOURCE_PROBATION_FAILURES"
            )
