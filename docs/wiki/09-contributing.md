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
    git clone https://github.com/your-repo/configstream.git
    cd configstream
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

## Pull Request Workflow

1.  Create a new branch for your feature or fix.
2.  Write code and tests.
3.  Ensure all checks pass locally (`pytest`, `flake8`, `mypy`).
4.  Submit a Pull Request with a clear description of your changes.
5.  Address any review comments.

## Project Structure
*   `src/configstream`: Main Python package.
*   `src/go`: Go-based high-performance components.
*   `frontend`: Web interface assets.
*   `tests`: Test suite.
*   `docs/wiki`: Documentation.
