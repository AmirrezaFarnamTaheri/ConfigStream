# Phase 4: Testing Engine - Analysis Report (Deep Scan)

## 4. Overview
This phase analyzes the testing engine, focusing on the Go-based sidecar (`GoBatchTester`) and the auxiliary tools (`scanner`, `utls_client`).

## 4.1. Go Sidecar Integration (`src/go/tester/main.go`)

### 4.1.1. Core Logic & Concurrency
**Analysis**:
*   **JSON Decoder**: Use of `json.NewDecoder` is correct and robust against 64KB token limits of `bufio.Scanner`.
*   **Panic Recovery**: Implements global and per-worker panic recovery. This prevents a single malformed proxy from crashing the daemon.
    *   **Logging**: Logs panics to stderr. `GoBatchTester` (Python) monitors stderr.
*   **Port Binding**:
    *   `port := 10000 + getRandomInt(50000)`.
    *   **Race Condition**: Uses random ports. While statistical collision probability is low with 50k ports, it's non-zero.
    *   **Retry Logic**: `MaxRetries` loop handles binding failures gracefully.
    *   **Safety**: Explicitly avoids `net.Listen` check (which is a TOC/TOU race). Just attempts to start Sing-box.
*   **Context Propagation**:
    *   `testProxyWithContext` creates a child context with timeout.
    *   Passes `ctx` to `setupSingbox` and `testLatency`.
    *   **Leak Prevention**: `defer cancel()` ensures context cleanup.

### 4.1.2. Networking & Transport
**Analysis**:
*   `http.Transport`:
    *   `DisableKeepAlives: true`: Critical for avoiding file descriptor exhaustion when testing thousands of proxies (ephemeral ports).
    *   `MaxIdleConns: -1`: Ensures no pooling.
*   **SOCKS5**: Forces `socks5://127.0.0.1:%d`.
*   **Honeypot Logic**:
    *   Generates HMAC-SHA256 signature of `timestamp-id`.
    *   Verifies signature in response.
    *   **Robustness**: Handles non-200 status codes (fails safe, returns false).

### 4.1.3. SingBox Configuration
**Analysis**:
*   Uses `box.New(boxOpts)` directly.
*   **Registry**: Implicitly uses the global registry via `box.New`. Since Sing-box v1.9, this is thread-safe for *execution*, but configuration parsing (`json.Unmarshal` into `option.Options`) relies on the global registry being populated.
    *   **Risk**: If multiple tests run in parallel goroutines, `box.New` might race if it modifies global state? No, `box.New` creates a new instance. The registry is static.
*   **Inbound**: Changed from "mixed" to "socks" to fix `missing endpoint registry` errors in newer Sing-box versions.

## 4.2. Go Scanner (`src/go/tester/scanner/scanner.go`)

### 4.2.1. WireGuard Handshake
**Analysis**:
*   **Packet Construction**:
    *   Builds a valid-looking Initiation packet (Type 1).
    *   Generates random Ephemeral key (`curve25519.ScalarBaseMult`).
    *   **Optimization**: Fills Encrypted Static/Timestamp with random noise.
    *   **Validity**: This is technically invalid crypto (MACs are wrong), but sufficient to trigger a "Cookie Reply" (Type 4) or "Under Load" response from Cloudflare servers, which proves liveness and RTT.
*   **Concurrency**:
    *   Uses `sync.WaitGroup` and semaphore channel `sem` to limit workers.
    *   **Safety**: Correctly waits for all goroutines.

### 4.2.2. IP Generation
**Analysis**:
*   `generateIPList`: Iterates CIDRs.
*   **Memory**: Generates *all* IPs in memory slice `[]string`.
    *   **Risk**: `/24` is small (256 IPs). Cloudflare ranges are small. If user adds a `/16`, this slice becomes huge (65k strings).
    *   **Recommendation**: Use a generator/iterator instead of pre-allocating the full list if larger ranges are expected.

## 4.3. uTLS Client (`src/go/utls_client/main.go`)

### 4.3.1. Purpose
**Analysis**:
*   **Status**: Proof-of-Concept (PoC).
*   **Limitations**: Hardcoded to `www.google.com`. Does not support proxy routing (SOCKS5 dialing).
*   **Usage**: Not currently used by the main pipeline? (Pipeline uses `GoBatchTester` / `SingBoxTester`).
    *   **Action**: Mark as experimental or integrate into the main tester if fingerprinting checks are needed.

## 4.4. Rust FFI (`src/rust/ss_checker`)

### 4.4.1. Implementation
**Analysis**:
*   **Logic**: String checking (`contains("method")`).
*   **Validation**: Weak. It confirms JSON structure but doesn't validate cryptographic parameters.
*   **Utility**: Likely unused in favor of Python's `parse_ss`.

## Recommendations
1.  **Scanner Optimization**: Refactor `generateIPList` to be an iterator/channel generator to support large CIDRs without OOM.
2.  **uTLS Integration**: The `utls_client` is isolated. Consider merging its logic into the main `tester` binary to allow fingerprint verification of proxies.
3.  **Honeypot Secret**: Ensure `HoneypotSecret` env var is documented and set in CI/Prod.
