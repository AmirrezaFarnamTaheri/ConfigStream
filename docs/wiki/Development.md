# Development Guide

Welcome to ConfigStream v2.0 development!

## Environment Setup

1.  **Python:** Python 3.10+ required.
    ```bash
    pip install -e ".[dev]"
    ```
2.  **Go:** Go 1.21+ required for the tester.
    ```bash
    cd src/go/tester
    go mod tidy
    go build -o configstream-tester .
    ```
3.  **Frontend:** No build step required (Vanilla JS), but `playwright` is needed for testing.
    ```bash
    playwright install chromium
    ```

## Core Modules

### 1. `src/configstream/pipeline_core/`
The heart of the system.
-   `orchestrator.py`: Manages the flow.
-   `output_handler.py`: **NEW** Handles the Intelligence phase (Scan -> Wash -> Chain -> Write).

### 2. `src/configstream/intelligence/`
The "Brain" of v2.0.
-   `washer/core.py`: Wraps proxies in WARP.
-   `washer/chaining.py`: Generates topology-aware chains.
-   `vectors.py`: Generates AI feature vectors.

### 3. `src/go/tester/`
The "Muscle".
-   `main.go`: SOCKS5 Verifier.
-   `scanner/`: **NEW** High-performance UDP scanner for Cloudflare endpoints.

## Testing

Run unit tests:
```bash
pytest tests/unit
```

Run E2E tests (simulated):
```bash
pytest tests/e2e
```

**Note:** Some tests require the Go binary to be present in the path or project root.

## Contribution Workflow

1.  Create a feature branch.
2.  Implement changes.
3.  Run `black .`, `flake8 .`, `mypy .`
4.  Run `pytest`.
5.  Submit PR.
