# Go Sidecar Batch Tester & IPC Protocol Audit

## 1. Go Sidecar IPC & Process Lifecycle Diagram

```text
+-----------------------+                            +-----------------------------------+
| Python Manager        |                            | Go Sidecar Daemon (main.go)       |
| (GoBatchTester)       |                            |                                   |
|                       |      stdin (NDJSON)        | +-------------------------------+ |
| +-------------------+ | -------------------------> | | JSON Decoder (os.Stdin)       | |
| |   Batch Queue     | |                            | +---------------+---------------+ |
| +-------------------+ |                            |                 |                 |
|                       |                            |                 v                 |
| +-------------------+ |      stdout (NDJSON)       | +-------------------------------+ |
| | Background Reader | | <------------------------- | | Worker Pool (testProxy)       | |
| +-------------------+ |                            | +---------------+---------------+ |
|                       |                            |                 |                 |
| +-------------------+ |      stderr (Logs)         |                 v                 |
| | Heartbeat/Restart | | <------------------------- | +-------------------------------+ |
| +---------+---------+ |                            | | sing-box instance (per proxy) | |
|           |           |                            | +-------------------------------+ |
+-----------|-----------+                            +-----------------------------------+
            | (Process Control: Terminate -> Wait(2s) -> Kill)
            v
       [ OS Process ]
```

## 2. Timeout & Failure Counter Contract Verification Table

| Requirement | Status | Implementation Reference | Notes |
|-------------|--------|--------------------------|-------|
| 5 Consecutive Timeout Limit | ✅ PASS | `manager.py:105` `_max_consecutive_timeouts = 5` | Properly checked in `test_batch`. Exceeding this disables the daemon (`self.available = False`). |
| Reset Counter on Success | ✅ PASS | `manager.py:747` `self._consecutive_timeouts = 0` | Counter resets correctly at the end of a successfully completed batch. |
| Daemon Restart Logic | ✅ PASS | `manager.py:640` | The manager restarts the daemon and properly awaits its completion (`safe_wait_for` 30s) before processing further batches. |

## 3. JSON Array Payload Framing & Parser Robustness Audit

**Python Side (`manager.py`):**
- **Framing**: Uses NDJSON formatting properly (`\n.join(_json_str(i) for i in inputs) + "\n"`).
- **JSON Array format**: `config` payload is stringified as a valid JSON array of outbounds, completely avoiding concatenated JSON.

**Go Side (`main.go`):**
- **Robustness**: Uses `json.NewDecoder(os.Stdin)` which natively supports stream/NDJSON decoding. Contains an error backoff (`decodeErrors >= 5` triggers exit) to prevent infinite loops on corrupted IPC pipes.
- **Config Parsing**: `parseConfig` attempts to unmarshal the `config` string as a JSON array first. If it fails, it falls back to parsing as a single object or a full `options` struct.

*Audit Result*: Compliant with Rule 4 contract. The stringified inner payload design (`ConfigStr string`) avoids nested AST parsing overhead during IPC transport, deferring it until the worker thread invokes `parseConfig`.

## 4. Sub-process I/O & Memory Leak Assessment

- **I/O Pipes**: Sub-process standard pipes (`stdin`, `stdout`, `stderr`) are effectively consumed by asynchronous background loops (`_read_loop` and `_read_stderr_loop`). This eliminates the risk of pipe buffer deadlocks.
- **Memory Leaks**:
  - **Python**: `_pending_futures` map is rigorously cleared in `_cleanup_pending` and timeout handlers, preventing Future leaks.
  - **Go**: Each test spins up an isolated `sing-box` instance with a context timeout. Crucially, deferred panics during `instance.Close()` are safely recovered. 
  - **Zombie Cleanup**: `GoBatchTester.close()` implements graceful termination. It attempts `.terminate()`, awaits `2.0` seconds, and falls back to `.kill()`. This guarantees process reaping on both Linux and Windows environments.

## 5. Code Optimization Patches

1. **Avoid Double JSON Serialization**: Currently, Python serializes the `outbounds` array to a string, and puts it in the `config` field, serializing the whole payload again. On the Go side, it decodes the payload, then parses the `config` string.
   - *Patch Suggestion*: Change `ConfigStr string` to `Config json.RawMessage` in Go. This allows passing the config block natively without escaping strings and avoids double-serialization costs.
2. **Scanner UDP Optimization**: The scanner relies on a global `pending` map. Under high worker concurrency, `sync.Map` scaling could bottleneck.
   - *Patch Suggestion*: Shard the map or encode the start-timestamp / index securely within the WireGuard initiation packet's 3-byte `Reserved` or 4-byte `SenderIndex` fields to achieve a completely stateless scanner.
