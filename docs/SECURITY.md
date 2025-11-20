# Security Architecture

ConfigStream implements a multi-layered security model to ensure the safety of aggregated proxies.

## 1. Pipeline Security
*   **No External Databases**: All state is managed via Git artifacts to prevent injection attacks on persistent storage.
*   **Dependency Pinning**: Strict versioning in `pyproject.toml` prevents supply chain attacks.

## 2. Proxy Validation (Active Scanning)

### Honeypot Detection
Before listing a proxy, we actively probe its IP address for suspicious open ports (e.g., Telnet, SSH) that indicate a compromised server or a honeypot designed to log traffic.
*   *Implementation*: `src/configstream/security/honeypot.py`

### TLS Fingerprint Randomization (uTLS)
To evade advanced firewalls that fingerprint Python's standard `ssl` library, we use a Go-based sidecar (`src/go/utls_client`) to generate randomized TLS Client Hellos (Chrome, Firefox, iOS, Random).
*   *Implementation*: `src/configstream/security/utls_wrapper.py`

### Shadowsocks Verification (Rust FFI)
We use the official Rust core of Shadowsocks via FFI to ensure robust crypto verification, replacing slower Python implementations.
*   *Implementation*: `src/configstream/security/ss_ffi.py`

## 3. Content Integrity
*   **MITM Detection**: We check for suspicious certificate issuers (e.g., "Fiddler", "GoProxy") during the handshake.
*   **HTML Injection**: We visit a control page and verify that no scripts or iframes are injected into the response.
