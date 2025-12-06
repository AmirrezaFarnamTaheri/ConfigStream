# Getting Started

## Prerequisites

*   **Python 3.10+**: The core logic is Python-based.
*   **Go 1.21+**: Required to build the high-performance tester.
*   **Git**: For version control.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/configstream.git
    cd configstream
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -e ".[dev]"
    ```

3.  **Build the Go Tester:**
    ```bash
    cd src/go/tester
    go build -o configstream-tester .
    # Move it to the root or ensure it's in your PATH
    mv configstream-tester ../../../
    ```

## First Run

To run a simple test pipeline locally:

```bash
# Run a single batch (Batch 1)
python -m configstream.cli merge --batch 1 --verbose
```

To run the merge process (requires previous batch outputs):

```bash
python -m configstream.cli merge
```

## Configuration Basics

Configuration is managed via `src/configstream/config.py` and environment variables.

*   `MAX_WORKERS`: Controls concurrency (default: adaptive).
*   `TEST_TIMEOUT`: Timeout for proxy tests (default: 15s).
*   `WARP_KEY_POOL`: (Optional) JSON array of WARP keys for washing.
*   `WARP_CLEAN_IPS`: (Optional) JSON array or comma-separated list of clean IPs.

See [Configuration Reference](configuration.md) for full details.
