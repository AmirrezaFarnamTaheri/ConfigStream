# ConfigStream Architecture Documentation

## Overview

ConfigStream is a VPN configuration aggregator that fetches, tests, and publishes working proxy configurations from public sources.

## Design Principles

### 1. Module Organization

#### Core Modules (Production)
- **models.py**: Data models (Proxy class)
- **parsers.py**: Configuration parsing and validation
- **core.py**: Core parsing logic and geolocation
- **pipeline.py**: Main orchestration and workflow
- **testers.py**: Proxy connectivity testing
- **output.py**: Multiple output format generation
- **geoip.py**: Geolocation database management
- **cli.py**: Command-line interface
- **cli_errors.py**: Error handling and CLI exceptions
- **config.py**: Application settings and configuration
- **logging_config.py**: Logging setup and filters
- **performance.py**: Performance tracking and metrics
- **statistics.py**: Statistics computation
- **async_file_ops.py**: Non-blocking file I/O operations

#### Utility Modules (For Testing/Examples)
These modules are fully tested but not currently used in production pipeline:
- **fetcher.py**: Advanced HTTP fetching with retry logic (310 lines)
- **filtering.py**: Fluent API for proxy filtering (73 lines)
- **events.py**: Event bus for pub/sub patterns (74 lines)
- **scheduler.py**: Scheduled proxy retesting (85 lines)
- **monitor.py**: Health monitoring (50 lines)
- **security/rate_limiter.py**: Token bucket rate limiting (36 lines)

**Why keep these?**
- Fully tested (100% coverage for most)
- Provide examples for extending functionality
- May be activated in future versions
- Show design patterns for contributors

### 2. Code Patterns

#### When to Use Classes vs Functions

**Use Functions for:**
- Stateless operations (parsing, validation, conversion)
- Pure transformations with no side effects
- Examples: `parse_config()`, `_safe_b64_decode()`

**Use Classes for:**
- Stateful operations requiring initialization
- Resource management (connections, pools)
- Examples: `SingBoxTester`, `PerformanceTracker`

#### Import Conventions

**Standard Import Paths:**
```python
# Data models
from .models import Proxy  # ALWAYS use .models

# Core functions
from .core import parse_config, geolocate_proxy

# Configuration
from .config import AppSettings
```

**Anti-pattern:**
```python
from .core import Proxy  # WRONG - Proxy is defined in .models
```

#### Error Handling Standards

**Pattern 1: Silent Failure with Logging**
Use for parsing operations where failure is expected:
```python
def _parse_vmess(config: str) -> Proxy | None:
    try:
        # Parsing logic
        return Proxy(...)
    except Exception as e:
        logger.debug(f"Failed to parse VMess: {e}")
        return None
```

**Pattern 2: Error Propagation**
Use for critical operations that should fail the entire workflow:
```python
async def download_geoip_dbs():
    try:
        # Download logic
    except Exception as e:
        logger.error(f"Failed to download GeoIP: {e}")
        raise  # Propagate to caller
```

**Pattern 3: Custom Exceptions**
Use for CLI operations that need specific exit codes:
```python
class CLIError(Exception):
    exit_code = 1

raise SourcesFileNotFoundError("sources.txt not found")
```

### 3. Async Patterns

#### File I/O
**Always use async file operations** to avoid blocking the event loop:

```python
# Good
from .async_file_ops import read_file_async, write_file_async
content = await read_file_async("file.txt")

# Bad
content = Path("file.txt").read_text()  # Blocks event loop!
```

#### Network Operations
All network calls should be async:
```python
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        return await response.text()
```

### 4. Security Considerations

#### Input Validation
- **Base64 Decoding**: Maximum size limits (5MB input, 10MB output)
- **Config Validation**: Plausibility checks before parsing
- **URL Validation**: Protocol and domain validation

#### Size Limits
```python
MAX_B64_INPUT_SIZE = 5 * 1024 * 1024      # 5MB
MAX_B64_OUTPUT_SIZE = 10 * 1024 * 1024    # 10MB
MAX_CONFIG_LINES = 50_000                  # 50k lines
MAX_LINE_LENGTH = 8192                     # 8KB per line
```

#### Sensitive Data Handling
- Logs can mask credentials when `MASK_SENSITIVE_DATA=true`
- Proxy configs may contain UUIDs - handle with care

### 5. Testing Strategy

#### Coverage Goals
- Core modules: 95%+ coverage
- Utility modules: 90%+ coverage
- CLI: 90%+ coverage (excluding OS-specific paths)

#### Test Organization
```
tests/
├── test_core.py           # Core parsing and geolocation
├── test_parsers.py        # Parser functions
├── test_parser_validation.py  # Security validations
├── test_pipeline.py       # End-to-end pipeline tests
├── test_testers.py        # Proxy testing
├── test_output.py         # Output generation
├── test_cli.py            # CLI commands
└── test_*.py              # One test file per module
```

#### Testing Patterns
- Use `pytest-asyncio` for async tests
- Use `pyfakefs` for file system mocking
- Use `pytest-aiohttp` for HTTP server mocking

### 6. Performance Considerations

#### Concurrency
- **Default workers**: 10 concurrent proxy tests
- **File I/O pool**: 10 threads for async file operations
- **HTTP timeout**: 10 seconds default

#### Optimization Strategies
1. **Async file operations**: Saves ~190ms per 20 files
2. **Concurrent testing**: Tests 10 proxies simultaneously
3. **Early filtering**: Remove invalid configs before testing

### 7. Output Formats

Supported formats:
- **Base64 Subscription**: Universal V2Ray clients
- **Clash YAML**: Clash clients
- **Sing-box JSON**: Sing-box clients
- **Shadowrocket**: iOS Shadowrocket
- **Quantumult**: iOS Quantumult
- **Surge**: iOS/macOS Surge

### 8. Extension Points

#### Adding New Protocols
1. Add parser function to `parsers.py`:
   ```python
   def _parse_newprotocol(config: str) -> Proxy | None:
       # Parsing logic
       return Proxy(...)
   ```

2. Register in `core.py`:
   ```python
   PROTOCOL_PARSERS = {
       "newprotocol://": _parse_newprotocol,
       # ...
   }
   ```

#### Adding New Output Formats
1. Add generator function to `output.py`:
   ```python
   def generate_newformat_config(proxies: List[Proxy]) -> str:
       # Generation logic
       return formatted_output
   ```

2. Call in `pipeline.py`:
   ```python
   newformat_content = generate_newformat_config(proxies)
   await write_file_async(output_dir / "config.newformat", newformat_content)
   ```

### 9. Deployment

#### GitHub Actions Pipeline
1. **Validation**: Linting, type checking
2. **Testing**: Full test suite with coverage
3. **Pipeline**: Fetch, test, publish configs
4. **Deployment**: Auto-deploy to GitHub Pages

#### Scheduling
- **Hourly**: Re-test existing proxies
- **Every 3 hours**: Fetch new sources and full pipeline
- **On push**: Validation and testing only

### 10. Known Limitations

1. **GeoIP Accuracy**: Based on MaxMind databases (95% accurate)
2. **Public Proxies**: No guarantee of privacy or security
3. **Rate Limiting**: Sources may rate-limit requests
4. **Windows Support**: Uses SelectorEventLoop (not ProactorEventLoop)

### 11. Future Enhancements

Potential areas for improvement:
1. **Activate utility modules** (filtering, events, scheduler)
2. **Advanced filtering UI** on GitHub Pages
3. **Historical statistics** tracking
4. **Source reliability scoring**
5. **Proxy health trends** over time

---

## Questions?

- Check the code comments for inline documentation
- Review test files for usage examples
- See CONTRIBUTING.md for development guidelines
