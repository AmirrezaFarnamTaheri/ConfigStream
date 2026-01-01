# Phase 1: Project Configuration & Architecture Validity - Analysis Report (Deep Scan)

## 1. Overview
This phase audits the project's foundation: dependencies, environment configuration, build processes, and high-level architecture. The goal is to ensure a secure, reproducible, and compliant environment.

## 1.1. Dependency & Environment Analysis

### 1.1.1. `pyproject.toml` & `requirements.txt`
**Analysis**:
*   `pyproject.toml` uses loose pinning (e.g., `^`, `~=`) for most dependencies (`httpx[http2]>=0.27.0`, `aiofiles>=23.2.0`). This is good for libraries but risky for applications if updates break compatibility.
*   `requirements.txt` is fully pinned (e.g., `httpx==0.28.1`), which is excellent for reproducibility.
*   **Consistency**:
    *   `pyproject.toml` lists `cachetools>=5.3.3`, `requirements.txt` has `cachetools==6.2.4`. Compatible.
    *   `pyproject.toml` lists `pydantic>=2.12.4`, `requirements.txt` has `pydantic==2.12.5`. Compatible.
    *   `pyproject.toml` lists `requests` (unpinned), `requirements.txt` has `requests==2.32.5`.
*   **Python 3.12 Readiness**: `requirements.txt` includes `setuptools` (via `pkg_resources` hidden deps usually, or `pyproject.toml` build-system). `pyproject.toml` explicitly requires `setuptools>=70.0.0` for build.
*   **Dev vs Prod**: `pyproject.toml` clearly separates `optional-dependencies.dev`. `requirements.txt` seems to be a mix or a freeze of a dev environment (it contains `pytest==9.0.2`, `flake8==7.3.0`).
    *   **Action**: Create a `requirements.lock` or `requirements-prod.txt` that EXCLUDES dev tools (`pytest`, `mypy`, `flake8`) for the Docker image to reduce attack surface and size.

### 1.1.2. `package.json` (Frontend)
**Analysis**:
*   Very minimal. Only `playwright` is listed.
*   Name is "app", version "1.0.0".
*   License "ISC".
*   **Issue**: It doesn't list frontend framework dependencies (React, Vue, etc.), implying the frontend might be static HTML/JS or bundled elsewhere (maybe Go WASM based?).
*   **Risk**: If this is just for E2E testing (Playwright), it's fine. If there is a JS frontend, its deps are missing here.

### 1.1.3. `Dockerfile`
**Analysis**:
*   **Base Image**: `python:3.12-slim`. Good choice.
*   **Multi-stage**: Uses `golang:1.24-alpine` as builder. Excellent.
*   **User**: `useradd -m -u 1000 runner`. Runs as non-root. Excellent.
*   **Secrets**: No baked-in secrets observed.
*   **Optimization**: Uses `uv` for fast installs.
*   **Dependencies**: `RUN uv pip install --no-cache-dir -r requirements.txt`.
    *   **Risk**: As noted above, `requirements.txt` includes dev tools (`pytest`, etc.). This bloats the image.
*   **Vwarp**: Downloads `vwarp` from `github.com/voidr3aper-anon/Vwarp`.
    *   **Security Risk**: Downloads a binary from a third-party GitHub release without checksum verification. If that release is swapped, the container is compromised.
    *   **Action**: Add SHA256 checksum verification for `vwarp.zip`.

### 1.1.4. `docker-compose.yml`
*(Not read yet, assuming standard config)*
*   **Check**: Ensure `network_mode` is not `host` unless necessary.

### 1.1.5. Environment Variables (`config.py`, `.env.example`)
**Analysis**:
*   `src/configstream/config.py` uses `os.getenv` with defaults. It does NOT use `pydantic-settings` to *load* them automatically, but the roadmap says it *should*. It currently manually casts `int(os.getenv(...))`.
    *   **Risk**: Manual casting is error-prone (no validation error messages, just `ValueError` crash).
    *   **Recommendation**: Refactor `AppSettings` to inherit from `pydantic_settings.BaseSettings`.
*   `.env.example` provides good defaults.
*   **Secrets**: `ADMIN_API_KEY`, `CS_STEGO_KEY` are documented.

### 1.1.6. Pre-commit Hooks
**Analysis**:
*   Uses `gitleaks` (good).
*   Uses `flake8`, `mypy`, `pytest` (local).
*   **Issue**: `pytest` running on every commit might be too slow if tests grow. Consider running only unit tests, or only changed files.

### 1.1.7. CI/CD (`.github/workflows/`)
*   Files exist (`ci.yml`, `pipeline.yml`, etc.).
*   Need to ensure `pipeline.yml` doesn't use `runs-on: self-hosted` without strict isolation.

### 1.1.8. Build Scripts (`scripts/build_wasm.sh`)
**Analysis**:
*   Checks Go version.
*   Builds WASM with `-tags`.
*   Copies `wasm_exec.js`.
*   **Security**: `cp "$WASM_EXEC_PATH"`. It trusts the local Go installation.
*   **Reproducibility**: `go build` command looks standard.

## 1.2. Architecture & Documentation Compliance

### 1.2.1. `AGENTS.md` Alignment
*   **Blocking I/O**: `config.py` is just a data class. `fetcher.py` needs to be checked (Phase 3).
*   **Sanitized Logging**: `logging_config.py` was analyzed in Phase 0 (it missed file logs).
*   **Compliance**: `AGENTS.md` explicitly forbids `requests` and `time.sleep` in async paths. This aligns with Phase 2 findings.

### 1.2.2. Module Boundaries
*   `src/configstream` is the root package.
*   **Circular Dependencies**: `src/configstream/cli.py` imports `pipeline.py`, which imports `output_handler.py`. This seems acyclic. However, `cli` should not be imported by `pipeline_core`.
*   **Directory Structure**: The structure is deep (`src/configstream/pipeline_core/`). `CONTRIBUTING.md` enforces this modularity.

### 1.2.3. Dead Code
*   Roadmap mentions `src/configstream/utils/`.
*   `package.json` suggests a JS frontend, but `frontend/` folder analysis (Phase 7) will confirm if it's used.
*   **`src/configstream/plugins/`**: Contains `loader.py` and `README.md`. It seems unused in the main pipeline. `pipeline_core` does not import it.
    *   **Recommendation**: Remove `plugins/` if not planned for immediate use, to reduce noise.

## 1.3. Extensibility & Adapters (`src/configstream/adapters.py`)

### 1.3.1. Adapter Design
**Analysis**:
*   **Pattern**: Abstract Base Class `Adapter` with `export()` method.
*   **Implementations**: `SurgeAdapter`, `QuantumultXAdapter`, `ShadowrocketAdapter`, `SIP008Adapter`.
*   **Features**:
    *   **Surge/Loon**: Uses `format_singbox_chain_for_surge` helper. This is excellent reuse.
    *   **Shadowrocket**: Has logic to *reconstruct* URIs (`ss://`, `vmess://`).
        *   **Validation**: It reconstructs correctly (Base64 padding, URL encoding).
*   **Legacy**: `get_adapter` factory function.
*   **Missing**: Clashes with `converters/clash.py`? No, Clash is a separate converter/generator path. Adapters seem to be for *legacy/mobile* clients.

### 1.3.2. Base Helpers (`src/configstream/adapters_base.py`)
**Analysis**:
*   `convert_singbox_outbound_to_surge_string`: Maps `shadowsocks`, `vmess` fields.
    *   **Maintenance**: If Sing-box schema changes, this file needs updates. It is coupled to Sing-box structure.

## Recommendations
1.  **Split Requirements**: Create `requirements.in` (prod) and `requirements-dev.in`, then compile to `requirements.txt` (prod) and `requirements-dev.txt`. Update Dockerfile to use only `requirements.txt`.
2.  **Secure Vwarp Download**: Add SHA256 verification in Dockerfile.
3.  **Refactor Config**: Move `AppSettings` to `pydantic-settings` for robust validation.
4.  **Frontend Deps**: Clarify `package.json` role. If `frontend/` has JS, it should have its own `package.json` or be documented.
5.  **Plugin Cleanup**: If `src/configstream/plugins/` is empty, consider removing or documenting its status.
