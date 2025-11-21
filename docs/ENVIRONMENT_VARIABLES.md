# Environment Variables Documentation

This document provides comprehensive information about all environment variables used in ConfigStream.

---

## Table of Contents

- [Core Configuration](#core-configuration)
- [Directory Paths](#directory-paths)
- [Database Configuration](#database-configuration)
- [Network Settings](#network-settings)
- [Security Settings](#security-settings)
- [Performance Tuning](#performance-tuning)
- [Logging Configuration](#logging-configuration)
- [Feature Flags](#feature-flags)
- [External Services](#external-services)

---

## Core Configuration

### `CONFIGSTREAM_ENV`
- **Type**: `string`
- **Default**: `production`
- **Valid Values**: `production`, `development`, `test`
- **Description**: Runtime environment mode
- **Example**: `CONFIGSTREAM_ENV=development`

### `CONFIG_FILE`
- **Type**: `path`
- **Default**: `None`
- **Description**: Path to external configuration file (YAML/JSON)
- **Example**: `CONFIG_FILE=/etc/configstream/config.yaml`

---

## Directory Paths

### `OUTPUT_DIR`
- **Type**: `path`
- **Default**: `./output`
- **Description**: Directory for generated proxy configuration files
- **Usage**: Where `proxies.json`, `metadata.json`, and all subscription formats are saved
- **Example**: `OUTPUT_DIR=/var/www/configstream/output`

### `FRONTEND_DIR`
- **Type**: `path`
- **Default**: `./frontend`
- **Description**: Directory containing frontend static files
- **Usage**: Used by web server to serve HTML/CSS/JS files
- **Example**: `FRONTEND_DIR=/usr/share/configstream/frontend`

### `DATA_DIR`
- **Type**: `path`
- **Default**: `./data`
- **Description**: Directory for persistent data (GeoIP databases, caches)
- **Example**: `DATA_DIR=/var/lib/configstream/data`

### `BACKUP_DIR`
- **Type**: `path`
- **Default**: `./backups`
- **Description**: Directory for automated database backups
- **Example**: `BACKUP_DIR=/var/backups/configstream`

### `SOURCES_DIR`
- **Type**: `path`
- **Default**: `./sources`
- **Description**: Directory containing source URL batch files
- **Example**: `SOURCES_DIR=/etc/configstream/sources`

---

## Database Configuration

### `DB_PATH`
- **Type**: `path`
- **Default**: `./data/configstream.db`
- **Description**: Path to SQLite database file
- **Example**: `DB_PATH=/var/lib/configstream/database.db`

### `CACHE_DB_PATH`
- **Type**: `path`
- **Default**: `./data/cache.db`
- **Description**: Path to cache database
- **Example**: `CACHE_DB_PATH=/tmp/configstream_cache.db`

### `DB_BACKUP_RETENTION_DAYS`
- **Type**: `integer`
- **Default**: `7`
- **Range**: `1-90`
- **Description**: Number of days to retain database backups
- **Example**: `DB_BACKUP_RETENTION_DAYS=14`

### `DB_WAL_MODE`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable SQLite Write-Ahead Logging for better concurrency
- **Example**: `DB_WAL_MODE=true`

---

## Network Settings

### `HTTP_TIMEOUT`
- **Type**: `integer`
- **Default**: `20`
- **Unit**: seconds
- **Range**: `5-120`
- **Description**: Global HTTP request timeout
- **Example**: `HTTP_TIMEOUT=30`

### `HTTP_MAX_RETRIES`
- **Type**: `integer`
- **Default**: `3`
- **Range**: `0-10`
- **Description**: Maximum number of HTTP request retries
- **Example**: `HTTP_MAX_RETRIES=5`

### `HTTP_CONNECT_TIMEOUT`
- **Type**: `integer`
- **Default**: `10`
- **Unit**: seconds
- **Description**: TCP connection timeout
- **Example**: `HTTP_CONNECT_TIMEOUT=15`

### `HTTP_READ_TIMEOUT`
- **Type**: `integer`
- **Default**: `15`
- **Unit**: seconds
- **Description**: HTTP read timeout
- **Example**: `HTTP_READ_TIMEOUT=20`

### `USER_AGENT`
- **Type**: `string`
- **Default**: `ConfigStream/1.3.0`
- **Description**: HTTP User-Agent header for requests
- **Example**: `USER_AGENT="Mozilla/5.0 (compatible; ConfigStream/1.3.0)"`

### `MAX_CONCURRENT_CONNECTIONS`
- **Type**: `integer`
- **Default**: `100`
- **Range**: `10-1000`
- **Description**: Maximum concurrent HTTP connections
- **Example**: `MAX_CONCURRENT_CONNECTIONS=200`

---

## Security Settings

### `STRICT_SECURITY`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Enable enhanced security checks (MITM detection, honeypot filtering)
- **Impact**: Slower testing but higher security
- **Example**: `STRICT_SECURITY=true`

### `ENABLE_HONEYPOT_DETECTION`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable honeypot proxy detection
- **Example**: `ENABLE_HONEYPOT_DETECTION=true`

### `HONEYPOT_TIMEOUT`
- **Type**: `integer`
- **Default**: `2`
- **Unit**: seconds
- **Description**: Timeout for honeypot detection checks
- **Example**: `HONEYPOT_TIMEOUT=3`

### `BLOCKLIST_UPDATE_INTERVAL`
- **Type**: `integer`
- **Default**: `3600`
- **Unit**: seconds
- **Description**: How often to refresh IP blocklist
- **Example**: `BLOCKLIST_UPDATE_INTERVAL=7200`

### `ENABLE_UTLS_VALIDATION`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Enable uTLS fingerprint randomization (requires Go binary)
- **Example**: `ENABLE_UTLS_VALIDATION=true`

### `ENABLE_SS_RUST_VALIDATION`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Enable Shadowsocks-Rust validation (requires Rust library)
- **Example**: `ENABLE_SS_RUST_VALIDATION=true`

---

## Performance Tuning

### `MAX_WORKERS`
- **Type**: `integer`
- **Default**: `10`
- **Range**: `1-100`
- **Description**: Maximum concurrent proxy test workers
- **Recommendation**: `2 × CPU_CORES` for I/O-bound workloads
- **Example**: `MAX_WORKERS=20`

### `CHUNK_SIZE`
- **Type**: `integer`
- **Default**: `50`
- **Range**: `10-500`
- **Description**: Number of proxies to test in each batch
- **Example**: `CHUNK_SIZE=100`

### `QUEUE_MAX_SIZE`
- **Type**: `integer`
- **Default**: `10000`
- **Range**: `100-100000`
- **Description**: Maximum size of internal work queue
- **Example**: `QUEUE_MAX_SIZE=50000`

### `CACHE_MAXSIZE`
- **Type**: `integer`
- **Default**: `10000`
- **Range**: `100-100000`
- **Description**: Maximum number of cached proxy test results
- **Example**: `CACHE_MAXSIZE=20000`

### `CACHE_TTL`
- **Type**: `integer`
- **Default**: `21600`
- **Unit**: seconds (6 hours)
- **Description**: Cache time-to-live for proxy test results
- **Example**: `CACHE_TTL=43200`

### `ENABLE_ADAPTIVE_WORKERS`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Dynamically adjust worker count based on system resources
- **Example**: `ENABLE_ADAPTIVE_WORKERS=false`

### `ADAPTIVE_WORKER_MIN`
- **Type**: `integer`
- **Default**: `5`
- **Description**: Minimum workers when adaptive scaling is enabled
- **Example**: `ADAPTIVE_WORKER_MIN=10`

### `ADAPTIVE_WORKER_MAX`
- **Type**: `integer`
- **Default**: `50`
- **Description**: Maximum workers when adaptive scaling is enabled
- **Example**: `ADAPTIVE_WORKER_MAX=100`

---

## Logging Configuration

### `LOG_LEVEL`
- **Type**: `string`
- **Default**: `INFO`
- **Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Global logging level
- **Example**: `LOG_LEVEL=DEBUG`

### `LOG_FORMAT`
- **Type**: `string`
- **Default**: `text`
- **Valid Values**: `text`, `json`
- **Description**: Log output format
- **Example**: `LOG_FORMAT=json`

### `LOG_FILE`
- **Type**: `path`
- **Default**: `None`
- **Description**: Path to log file (logs to stdout if not set)
- **Example**: `LOG_FILE=/var/log/configstream/app.log`

### `LOG_MAX_SIZE`
- **Type**: `integer`
- **Default**: `10485760`
- **Unit**: bytes (10 MB)
- **Description**: Maximum log file size before rotation
- **Example**: `LOG_MAX_SIZE=52428800`

### `LOG_BACKUP_COUNT`
- **Type**: `integer`
- **Default**: `5`
- **Description**: Number of rotated log files to keep
- **Example**: `LOG_BACKUP_COUNT=10`

### `ENABLE_PERFORMANCE_LOGGING`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Enable detailed performance metrics logging
- **Example**: `ENABLE_PERFORMANCE_LOGGING=true`

---

## Feature Flags

### `ENABLE_WEBSOCKET`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable WebSocket live feed endpoint
- **Example**: `ENABLE_WEBSOCKET=false`

### `ENABLE_ANALYTICS`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable analytics data collection
- **Example**: `ENABLE_ANALYTICS=false`

### `ENABLE_PWA`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable Progressive Web App features
- **Example**: `ENABLE_PWA=false`

### `ENABLE_SMART_SCHEDULING`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable intelligent proxy retest scheduling
- **Example**: `ENABLE_SMART_SCHEDULING=false`

### `ENABLE_ANOMALY_DETECTION`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable anomaly detection for source poisoning attacks
- **Example**: `ENABLE_ANOMALY_DETECTION=false`

### `CIRCUIT_BREAKER_ENABLED`
- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable circuit breaker for failing sources
- **Example**: `CIRCUIT_BREAKER_ENABLED=false`

### `CIRCUIT_BREAKER_THRESHOLD`
- **Type**: `integer`
- **Default**: `5`
- **Range**: `1-20`
- **Description**: Consecutive failures before circuit opens
- **Example**: `CIRCUIT_BREAKER_THRESHOLD=10`

### `CIRCUIT_BREAKER_TIMEOUT`
- **Type**: `integer`
- **Default**: `60`
- **Unit**: seconds
- **Description**: Time before attempting to close circuit
- **Example**: `CIRCUIT_BREAKER_TIMEOUT=120`

---

## External Services

### `GEOIP_DATABASE_PATH`
- **Type**: `path`
- **Default**: `./data/GeoLite2-City.mmdb`
- **Description**: Path to GeoIP2 city database
- **Example**: `GEOIP_DATABASE_PATH=/usr/share/GeoIP/GeoLite2-City.mmdb`

### `GEOIP_ASN_DATABASE_PATH`
- **Type**: `path`
- **Default**: `./data/GeoLite2-ASN.mmdb`
- **Description**: Path to GeoIP2 ASN database
- **Example**: `GEOIP_ASN_DATABASE_PATH=/usr/share/GeoIP/GeoLite2-ASN.mmdb`

### `TELEGRAM_BOT_TOKEN`
- **Type**: `string`
- **Default**: `None`
- **Description**: Telegram bot API token for bot functionality
- **Example**: `TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

### `TELEGRAM_ADMIN_IDS`
- **Type**: `comma-separated list`
- **Default**: `None`
- **Description**: Telegram user IDs with admin access
- **Example**: `TELEGRAM_ADMIN_IDS=12345678,87654321`

### `VIRUSTOTAL_API_KEY`
- **Type**: `string`
- **Default**: `None`
- **Description**: VirusTotal API key for IP reputation checks (optional)
- **Example**: `VIRUSTOTAL_API_KEY=your_api_key_here`

---

## Web Server Settings

### `WEB_HOST`
- **Type**: `string`
- **Default**: `0.0.0.0`
- **Description**: Host address for web server to bind to
- **Example**: `WEB_HOST=127.0.0.1`

### `WEB_PORT`
- **Type**: `integer`
- **Default**: `8000`
- **Range**: `1024-65535`
- **Description**: Port for web server
- **Example**: `WEB_PORT=8080`

### `WEB_RELOAD`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Enable hot-reload for development
- **Example**: `WEB_RELOAD=true`

### `WEB_WORKERS`
- **Type**: `integer`
- **Default**: `1`
- **Range**: `1-16`
- **Description**: Number of web server worker processes
- **Example**: `WEB_WORKERS=4`

---

## Testing and Development

### `DRY_RUN`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Simulate proxy testing without actual network calls
- **Usage**: For testing pipeline logic
- **Example**: `DRY_RUN=true`

### `MOCK_FETCH`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Use mock data instead of fetching real sources
- **Example**: `MOCK_FETCH=true`

### `DEBUG_MODE`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Enable debug features (verbose logging, profiling)
- **Example**: `DEBUG_MODE=true`

### `PROFILE_ENABLED`
- **Type**: `boolean`
- **Default**: `false`
- **Description**: Enable performance profiling
- **Example**: `PROFILE_ENABLED=true`

---

## Example Configuration Files

### `.env.production`
```bash
# Production Configuration
CONFIGSTREAM_ENV=production

# Paths
OUTPUT_DIR=/var/www/configstream/output
DATA_DIR=/var/lib/configstream/data
BACKUP_DIR=/var/backups/configstream

# Performance
MAX_WORKERS=20
CHUNK_SIZE=100
CACHE_TTL=21600

# Security
STRICT_SECURITY=false
ENABLE_HONEYPOT_DETECTION=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/configstream/app.log

# Web Server
WEB_HOST=0.0.0.0
WEB_PORT=8000
WEB_WORKERS=4
```

### `.env.development`
```bash
# Development Configuration
CONFIGSTREAM_ENV=development

# Paths
OUTPUT_DIR=./output
DATA_DIR=./data

# Performance
MAX_WORKERS=5
CHUNK_SIZE=20

# Security
STRICT_SECURITY=true
ENABLE_HONEYPOT_DETECTION=true

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Web Server
WEB_HOST=127.0.0.1
WEB_PORT=8000
WEB_RELOAD=true

# Development
DEBUG_MODE=true
DRY_RUN=false
```

### `.env.test`
```bash
# Test Configuration
CONFIGSTREAM_ENV=test

# Paths
OUTPUT_DIR=./test_output
DATA_DIR=./test_data

# Performance
MAX_WORKERS=2
CHUNK_SIZE=10

# Testing
DRY_RUN=true
MOCK_FETCH=true

# Logging
LOG_LEVEL=WARNING
```

---

## Loading Environment Variables

### Using `.env` File (Recommended)

Create a `.env` file in the project root:

```bash
# .env
OUTPUT_DIR=/custom/path
MAX_WORKERS=20
LOG_LEVEL=INFO
```

ConfigStream automatically loads `.env` files using `python-dotenv`.

### Using Shell Export

```bash
export OUTPUT_DIR=/custom/path
export MAX_WORKERS=20
python -m configstream.cli merge --sources sources.txt
```

### Using Systemd Service

```ini
# /etc/systemd/system/configstream.service
[Service]
Environment="OUTPUT_DIR=/var/www/configstream/output"
Environment="MAX_WORKERS=20"
Environment="LOG_LEVEL=INFO"
ExecStart=/usr/local/bin/configstream merge --sources /etc/configstream/sources.txt
```

### Using Docker

```bash
docker run -e OUTPUT_DIR=/output -e MAX_WORKERS=20 configstream
```

Or with `.env` file:
```bash
docker run --env-file .env configstream
```

---

## Precedence Order

Environment variables are loaded in the following precedence (highest to lowest):

1. **Command-line arguments** (if applicable)
2. **Shell environment variables** (`export VAR=value`)
3. **`.env` file** in current directory
4. **Default values** in code

---

## Validation

ConfigStream validates environment variables on startup:

- Type checking (integer, boolean, string, path)
- Range validation (min/max values)
- Path existence checks (for required directories)
- Dependency validation (e.g., STRICT_SECURITY requires certain paths)

Invalid configurations will raise an error with a clear message.

---

## Security Notes

- Never commit `.env` files containing secrets to version control
- Use `.env.example` as a template without sensitive values
- Restrict file permissions on `.env`: `chmod 600 .env`
- Use secrets management tools (Vault, AWS Secrets Manager) in production
- Rotate API keys regularly
- Audit environment variables in production deployments

---

## Troubleshooting

### Environment variable not recognized

**Symptoms**: Variable changes don't take effect
**Solution**:
1. Check variable name spelling
2. Restart the application
3. Verify `.env` file location
4. Check shell export syntax

### Permission denied errors

**Symptoms**: Cannot create files in OUTPUT_DIR
**Solution**:
1. Verify directory exists and is writable
2. Check file permissions: `ls -la /path/to/dir`
3. Grant access: `chmod 755 /path/to/dir`

### Performance issues

**Symptoms**: Slow proxy testing
**Solution**:
1. Increase `MAX_WORKERS` (recommended: 2 × CPU cores)
2. Adjust `CHUNK_SIZE` based on network latency
3. Enable `ENABLE_ADAPTIVE_WORKERS`
4. Increase `CACHE_TTL` to reduce retesting

---

## Additional Resources

- [Configuration Documentation](./CONFIGURATION.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Security Best Practices](./SECURITY.md)
- [Performance Tuning Guide](./PERFORMANCE.md)

---

**Last Updated**: 2025-11-21
**Version**: 1.3.0
