# 09. Contributor Guide

We welcome contributions! This guide will help you get started.

## Development Environment

### Prerequisites
*   Python 3.10+
*   Go 1.21+ (for the Go Tester sidecar)
*   Docker (optional, for local containerized runs)

### Setup
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
    cd ConfigStream
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -e ".[dev]"
    ```
    This installs the package in editable mode along with development tools (flake8, mypy, pytest, etc.).

4.  **Install Playwright browsers (for E2E tests):**
    ```bash
    playwright install --with-deps
    ```

## Coding Standards

We enforce strict code quality standards.

*   **Formatting:** We use `black`.
    ```bash
    black .
    ```
*   **Linting:** We use `flake8`.
    ```bash
    flake8 src tests
    ```
*   **Type Checking:** We use `mypy`.
    ```bash
    mypy src
    ```

## Testing

*   **Run all tests:**
    ```bash
    pytest
    ```
*   **Run unit tests only:**
    ```bash
    pytest tests/unit
    ```
*   **Run E2E tests:**
    ```bash
    pytest tests/e2e
    ```

**Coverage Requirement:** We aim for >90% test coverage. Please write tests for any new features or bug fixes.

## Frontend Contributions

The frontend is a critical security boundary.
*   **Security (XSS)**:
    *   NEVER use `innerHTML` with user-supplied data unless sanitized with `DOMPurify`.
    *   Use `textContent` or `innerText` by default.
    *   Respect the Content Security Policy (CSP).
*   **Accessibility (a11y)**:
    *   Ensure all interactive elements have keyboard support (`tabindex`, `Enter`/`Space` handlers).
    *   Use ARIA roles (`role="menu"`, `aria-label`) where semantic HTML is insufficient.
*   **Testing**:
    *   Write tests for JS modules where possible.
    *   Verify UI changes in multiple browsers.

## Pull Request Workflow

1.  Create a new branch for your feature or fix.
2.  Write code and tests.
3.  Ensure all checks pass locally (`pytest`, `flake8`, `mypy`).
4.  Submit a Pull Request with a clear description of your changes.
5.  Address any review comments.

## Project Structure

| Directory | Purpose |
| :--- | :--- |
| `src/configstream/` | Main Python package — pipeline, parsers, testers, intelligence, generators, models |
| `src/configstream/intelligence/` | Intelligence layer — washer, chaining, evasion, adaptive timeout, circuit breaker |
| `src/configstream/generators/` | Output format generators (Sing-box, Clash, Plaintext, Split) |
| `src/configstream/converters/` | Proxy-to-config converters (Sing-box outbound, Clash dict) |
| `src/configstream/parsers/` | Protocol-specific URI parsers (VLESS, VMess, Trojan, SS, etc.) |
| `src/configstream/tools/` | CLI tools — VwarpTool, CensorshipLab (simulation), DNS scanner |
| `src/configstream/history/` | Proxy history tracking, trend export, analytics |
| `src/go/tester/` | Go sidecar — high-concurrency batch tester (NDJSON stdin/stdout) |
| `src/go/tester/wasm_main.go` | WASM tester for browser-side verification |
| `frontend/` | Web interface — Vanilla JS PWA, no build step |
| `frontend/assets/js/` | Core JS modules (main, analytics, statistics, proxies, dynamic-downloads, lab) |
| `tests/unit/` | Unit test suite (750+ tests) |
| `tests/e2e/` | End-to-end tests (Playwright) |
| `tests/fuzz/` | Fuzz testing for parsers |
| `scripts/` | CI helper scripts — merge_batches, deduplicate_sources, frontend verification |
| `tools/` | Standalone tools — Cloudflare Workers, DNS scanner, lab runner |
| `docs/wiki/` | Documentation wiki (this directory) |
| `sources/` | Batch source files (`batch_1.txt` … `batch_17.txt`) |

### Build the Go Tester

The Go tester is optional for basic development but required for full pipeline runs:
```bash
cd src/go/tester
go mod tidy
go build -o configstream-tester .
mv configstream-tester ../../../
```

**Note:** Some tests require the Go binary to be present in the project root or `PATH`.

## Related Documentation

*   **[Getting Started](getting_started.md)** — Full installation walkthrough (venv, Docker, Go tester, `.env`).
*   **[Architecture Deep Dive](02-architecture.md)** — Understand the pipeline before contributing.
*   **[Protocols & Parsing](03-protocols.md)** — Parser robustness rules, validation logic, credential recovery.
*   **[Security & Privacy](07-security.md)** — Security checklist, log sanitization rules, fail-open policy.
*   **[Troubleshooting](10-troubleshooting.md)** — Common dev environment issues and fixes.
