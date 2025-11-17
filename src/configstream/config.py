from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CONFIGSTREAM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    DEBUG: bool = False
    MAX_WORKERS: int = 10
    TIMEOUT: int = 10

    # Security
    TLS_TESTS_ENABLED: bool = True
    TLS_TESTS_ALLOW_INSECURE: bool = False
    # New Flags for Phase 2/3
    STRICT_SECURITY: bool = False  # If False, skips expensive integrity checks
    ALLOW_PRIVATE_IPS: bool = False # If True, allows 192.168.x.x (good for local dev)

    # Output
    RENAME_TEMPLATE: str = ""

    # Network
    DNS_CACHE_ENABLED: bool = True

    # Limits
    LAT_SOFT_CAP_MS: int = 1000

    # Resilience
    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_TRIP_CONN_ERRORS: int = 5
    CIRCUIT_OPEN_SEC: int = 60
    HEDGING_ENABLED: bool = False
    HEDGE_AFTER_MS: int = 500
