# Phase 8: Server & API - Analysis Report

## 8. Overview
This phase audits `src/configstream/server.py`, which is a FastAPI application serving the API, static assets, and WebSocket updates.

## 8.1. API Security

### 8.1.1. Input Validation
**Analysis**:
*   `country` and `protocol` params in `/api/proxies` are validated using `SAFE_PATH_PATTERN` (`^[a-zA-Z0-9_-]+$`).
*   **Path Traversal**:
    *   Explicit checks for `..`, `/`, `\`.
    *   `os.path.commonpath` check ensures the resolved path is strictly inside `OUTPUT_DIR`.
    *   This is robust.

### 8.1.2. Authentication
*   `/api/admin/notify-update`: Checks `ADMIN_API_KEY` env var.
    *   **Logic**: If `api_key` is set, payload must contain it. If `ENVIRONMENT` is `development` (default), it bypasses check if key is missing (allowing internal calls).
    *   **Risk**: Default is `development`. If deployed to prod without changing `ENVIRONMENT` or setting `ADMIN_API_KEY`, anyone can trigger updates (DoS risk, albeit low impact).

### 8.1.3. Rate Limiting
*   **Missing**: No rate limiting middleware observed in the code.
*   **Risk**: Public endpoints like `/api/proxies` could be hammered.

### 8.1.4. WebSocket Security
*   **Message Size**: Checks `len(data) > 1024`. Good protection against memory exhaustion.
*   **Logic**: Only handles "ping" and "sync".

## 8.2. Operational Safety

### 8.2.1. CORS Policy
*   **Origins**: `ALLOWED_ORIGINS` env var (default localhost).
*   **Regex**: `ALLOWED_ORIGIN_REGEX` (default `https://.*\.github\.io`).
    *   **Risk**: `https://.*\.github\.io` allows ANY GitHub Pages site to call the API. If the API is hosted publicly and uses cookies/auth (it doesn't seem to use cookies), a malicious page could exploit it. Since it's an open proxy aggregator, this is likely intended to allow community forks to use the backend.

### 8.2.2. Error Leakage
*   **500 Errors**: `HTTPException(500, "Internal Server Error")`. Stack traces are logged but not sent to client.
*   **FileResponse**: If file missing, returns 404.

## Recommendations
1.  **Rate Limiting**: Add `slowapi` or similar middleware to limit `/api/` calls.
2.  **Prod Default**: Change default `ENVIRONMENT` to `production` in `server.py` or ensure Dockerfile sets it.
3.  **CORS**: Document the security implication of the wildcard regex.
