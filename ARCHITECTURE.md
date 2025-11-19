# ConfigStream Architecture Documentation

## 1. Overview

ConfigStream is a high-performance VPN configuration aggregator designed for reliability and scalability. It fetches proxy configurations from diverse sources, validates them through a rigorous testing pipeline, and publishes them in multiple formats for end-user consumption. The architecture is built on modern asynchronous patterns in Python, ensuring non-blocking I/O for both network and file operations.

## 2. Core Design Principles

### Modularity and Separation of Concerns

The codebase is organized into distinct modules, each with a clear responsibility. This separation simplifies maintenance, testing, and future development.

-   **`pipeline.py` (Orchestrator)**: The heart of the application, responsible for orchestrating the entire workflow, from fetching and parsing to testing and output generation.
-   **`parsers.py` & `core.py` (Parsing & Validation)**: Handle the initial parsing and validation of raw proxy configurations. `core.py` is responsible for dispatching to the correct parser, while `parsers.py` contains the parsing logic for each protocol.
-   **`testers.py` (Proxy Testing)**: Contains the logic for testing proxy connectivity and performance.
-   **`output.py` (Output Generation)**: Generates the final output files in various formats (Base64, Clash, Sing-box, etc.).
-   **`concurrency_manager.py` (Concurrency Control)**: Implements a unified AIMD (Additive Increase, Multiplicative Decrease) concurrency controller to dynamically adjust system load for both fetching and testing.
-   **`http_client.py` (Networking)**: Manages a shared `httpx.AsyncClient` for all network requests, enabling connection pooling and HTTP/2 support.
-   **`logging_config.py` (Logging)**: Centralizes logging configuration, including support for structured JSON logging for machine-readable output.

### Asynchronous-First Approach

All I/O-bound operations (network requests, file access) are implemented using `asyncio` to maximize performance and prevent the event loop from blocking.

-   **Network Operations**: All network calls are made using an asynchronous HTTP client (`httpx`).
-   **File I/O**: File operations are offloaded to a thread pool via `async_file_ops.py` to avoid blocking the main thread.

### Dynamic Concurrency Management

To prevent system overload and adapt to varying network conditions, ConfigStream uses a unified concurrency model.

-   **AIMD Controller**: The `ConcurrencyManager` in `concurrency_manager.py` uses an AIMD algorithm to dynamically adjust the number of concurrent operations for both fetching and testing. This allows the system to automatically scale up during optimal conditions and back off when errors or high latency are detected.

### Intelligence Modules

The pipeline integrates several "intelligence" modules to improve efficiency and output quality:

-   **`source_quality.py`**: Tracks the performance of different sources and prioritizes fetching from those that consistently provide working proxies.
-   **`auto_detect.py`**: Provides fallback parsing mechanisms for unknown or malformed proxy configurations.
-   **`freshness.py`**: Filters out stale proxies based on their last-seen timestamp.
-   **`intelligent_fallback.py`**: Caches the last known-good set of proxies to ensure high availability, even if a pipeline run fails.

## 3. Data Flow

The data processing pipeline consists of the following stages:

1.  **Source Fetching**: The pipeline fetches raw proxy configurations from a list of sources (URLs or local files) using the `fetcher.py` module.
2.  **Parsing and Validation**: Raw configurations are parsed and validated by `parsers.py` and `core.py`. Invalid or insecure configurations are discarded.
3.  **Deduplication and Shuffling**: Proxies are deduplicated to ensure only unique configurations are tested. The list is then shuffled to randomize the testing order.
4.  **Proxy Testing**: Proxies are tested for connectivity and performance using the `testers.py` module. The `ConcurrencyManager` dynamically adjusts the number of concurrent tests.
5.  **Geolocation**: The geographic location of each working proxy is determined using an offline GeoIP database.
6.  **Output Generation**: The final list of working proxies is formatted into multiple output files by `output.py`.
7.  **Statistics and Metadata**: The pipeline generates `statistics.json` and `metadata.json` files, which provide data for the frontend UI.

## 4. Key Architectural Components

### Unified Concurrency Controller

The `ConcurrencyManager` is a key component for ensuring system stability and performance. It provides a centralized mechanism for controlling concurrency across the application.

-   **Generic Design**: The manager is designed to be generic and can be used to control concurrency for any resource-limited operation.
-   **Dynamic Adjustment**: It dynamically adjusts concurrency limits based on real-time performance metrics (latency, error rate), allowing the system to adapt to changing conditions.

### Structured JSON Logging

The `logging_config.py` module supports structured JSON logging, which is essential for modern observability.

-   **Machine-Readable Logs**: JSON logs are easy to parse and ingest into monitoring platforms like the ELK stack or Datadog.
-   **Rich Context**: Each log entry includes rich contextual information, such as a timestamp, log level, trace ID, and code location.

### Decoupled Frontend Configuration

The frontend UI is designed to be adaptable to backend configuration changes.

-   **`metadata.json`**: The pipeline writes key configuration values to `output/metadata.json`.
-   **Dynamic UI**: The frontend JavaScript fetches `metadata.json` and uses the values to dynamically render UI elements, such as charts. This removes hardcoded values from the frontend and allows the UI to be updated by changing the backend configuration.

## 5. Security Considerations

-   **Input Validation**: All inputs, from source URLs to raw proxy configurations, are rigorously validated to prevent injection attacks and other vulnerabilities.
-   **Resource Limiting**: The concurrency manager and rate limiters prevent the application from overwhelming external services or consuming excessive system resources.
-   **Sensitive Data Masking**: The logging system includes filters to mask sensitive data (e.g., UUIDs, email addresses) in log output.

## 6. Testing Strategy

The project maintains a comprehensive test suite to ensure code quality and prevent regressions.

-   **Unit Tests**: Each module has a corresponding set of unit tests to verify its functionality in isolation.
-   **Integration Tests**: The test suite includes integration tests that verify the interaction between different modules.
-   **High Coverage**: The project aims for high test coverage across the entire codebase.

## 7. Deployment

The application is deployed as a static website on GitHub Pages, with the backend pipeline running on a schedule using GitHub Actions.

-   **GitHub Actions**: The `.github/workflows/pipeline.yml` workflow automates the entire process of fetching, testing, and publishing proxy configurations.
-   **GitHub Pages**: The `output/` directory, which contains the generated output files and frontend assets, is deployed to the `gh-pages` branch, making the site publicly accessible.
