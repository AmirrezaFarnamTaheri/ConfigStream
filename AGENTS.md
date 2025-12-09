# ConfigStream Agents & Contributors Guidelines

## 1. Project Philosophy & Directives
ConfigStream is a **sovereignty-grade, zero-budget anti-censorship platform**. Every line of code must align with these core tenets:
1.  **Zero Budget**: Do not introduce dependencies on paid APIs, databases, or infrastructure. We rely exclusively on free GitHub Actions/Pages, public APIs, and user-provided resources.
2.  **Resilience**: The system must assume hostile network conditions. It must handle timeouts, blocklists, and unreliable sources gracefully (Fail-Open or Fail-Safe).
3.  **Security**: We operate in a high-risk domain. Logs must be sanitized. Inputs must be validated. No active scanning of third-party infrastructure.

## 2. Architectural Overview
The system follows a **Streaming Pipeline Architecture** (`Producer-Consumer`):

### Core Components
*   **Producer (`source_producer`)**: Fetches raw data from remote URLs or local files. It pushes raw content into a bounded `asyncio.Queue`.
    *   *Constraint*: Must not block on I/O. Uses `httpx` with adaptive timeouts.
*   **Consumer (`processing_consumer`)**: Pulls from the queue, parses, validates, tests, and aggregates proxies.
    *   *Parallelism*: Scalable via `num_consumers`.
    *   *Constraint*: CPU-intensive tasks (parsing, crypto) must run in `loop.run_in_executor`.
*   **Intelligence Layer**:
    *   `AdaptiveTimeout`: Adjusts timeouts based on historical latency.
    *   `CircuitBreaker`: Fails fast for unstable hosts.
    *   `SecurityValidator`: Enforces protocol compliance and sanitization.

## 3. Coding Standards

### Python
*   **Version**: Python 3.10+ (strict typing required).
*   **Style**: PEP 8. Enforced via `black` and `flake8`.
*   **Concurrency**:
    *   Use `asyncio` for I/O-bound tasks.
    *   Use `ProcessPoolExecutor` or `ThreadPoolExecutor` for CPU-bound tasks (e.g., parsing 10k lines).
    *   **NEVER** use blocking I/O (e.g., `requests`, `time.sleep`) in async functions.
*   **Logging**:
    *   Use `logging.getLogger(__name__)`.
    *   **Sanitization IS MANDATORY**: Wrap URLs/Errors with `SecurityValidator.sanitize_log_message`.
    *   Avoid log spam: Use debouncing (e.g., `CircuitBreaker` warnings) or sampling (e.g., logging only the first 5 dropped lines).

### Type Safety
*   All function signatures must have type hints.
*   Use `Optional`, `List`, `Dict`, `Union` from `typing`.
*   Check your work with `mypy`.

## 4. Specific Component Instructions

### Parsers (`src/configstream/parsers/`)
*   **Robustness**: Inputs are untrusted and often malformed.
    *   Handle trailing garbage in Base64 strings.
    *   Gracefully skip invalid lines without crashing the pipeline.
    *   Log drop rates/reasons at `DEBUG` level (or `WARNING` if failure rate > 50%).
*   **Robust Parsing**:
    *   **Credential Recovery**: For VLESS, Trojan, and Shadowsocks, if the primary credential field (e.g., username for UUID) is empty, the parser **MUST** check query parameters or other fields as a fallback before dropping the proxy.
    *   **Mandatory Fields**: If credentials are still missing after fallback attempts, parser MUST return `None` (drop).
    *   **Method Check**: Shadowsocks method must be valid (not "ss", "shadowsocks").
*   **Protocols**: Support for 20+ protocols (VLESS, VMess, Trojan, SS, SSR, Hysteria, Hysteria2, Tuic, WireGuard, SSH, SOCKS, HTTP, etc.) is required. Ensure correct mapping to the `Proxy` model.

### Fetcher (`src/configstream/fetcher.py`)
*   **Resilience**:
    *   Use `AdaptiveTimeout` to prevent stalling.
    *   Respect `CircuitBreaker` states to avoid hammering dead hosts.
    *   **Do not use ETag caching** (ConfigStream is stateless in CI).

### Security (`src/configstream/security_validator.py`)
*   **UUIDs**: For VMess/VLESS, a missing UUID is a fatal error. Drop the proxy.
*   **Sanitization**: Ensure tokens, passwords, and UUIDs are masked in logs.
*   **Blocklists**: Ensure `DEFAULT_BLOCKLIST` is updated before processing begins.

### Testing (`src/configstream/testers.py`)
*   **Dual Engine**:
    *   **Go Sidecar**: Preferred for performance/compatibility. It supports testing single proxies and **Chains** (lists of outbounds).
    *   **Python Fallback**: Minimal implementation for environments without the binary.
    *   **WASM Tester**: Browser-based verification component (`src/go/tester/wasm_main.go`). Must communicate via JS interop (`syscall/js`) and not use native networking.
*   **Washer Retesting**:
    *   Washed chains (Relay -> WARP) MUST be re-tested before inclusion in the final output to ensure end-to-end connectivity. This is handled in `scripts/merge/core.py`.
    *   **Washer Security**: Use Epoch-based rotation for WARP keys and sequential IP generation to prevent collisions.
*   **Cache**: Use `TestResultCache` to skip re-testing recently verified proxies. Ensure path persistence.

## 5. Testing & Verification
*   **Unit Tests**: Located in `tests/unit`. Run via `pytest`.
*   **E2E Tests**: Located in `tests/e2e`. Verify the full pipeline flow.
*   **Mocking**: Use `respx` for HTTP mocking and `unittest.mock` for internal components.
*   **Frontend**: If modifying UI, use Playwright to verify visual integrity.

## 6. Git & Version Control
*   **Diffs**: When generating patches, ensure context is accurate.
*   **Commit Messages**: Descriptive and git-agnostic.
*   **Artifacts**: Do not commit `output/`, `data/`, or `__pycache__` to the repo.

## 7. Checklist for Agents
Before submitting ANY code:
1.  [ ] Did you run `pytest`?
2.  [ ] Did you sanitize new log statements?
3.  [ ] Did you verify async compatibility (no blocking calls)?
4.  [ ] Did you update relevant documentation?
5.  [ ] If modifying `AGENTS.md`, does it reflect the new reality?

## 8. Common Pitfalls to Avoid
*   **Blocking the Event Loop**: E.g., large `base64.b64decode` on the main thread. -> Use `run_in_executor`.
*   **Unbounded Queues**: Can lead to OOM. -> Use `maxsize` for `asyncio.Queue`.
*   **Log Leaks**: Logging a raw URL with a token. -> Use `sanitize_log_message`.
*   **Path Assumptions**: Assuming `CWD` is always the repo root. -> Use `pathlib` with absolute resolution or relative to `__file__`.
