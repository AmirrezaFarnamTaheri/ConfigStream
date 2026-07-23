# WASM Sandbox & JavaScript Interop Audit

## 1. WASM Memory & JS Interop Architecture Diagram

```text
+---------------------+       +-----------------------+      +---------------------------+
|    Browser JS       |       |       Go WASM         |      |       Network Layer       |
|---------------------|       |-----------------------|      |---------------------------|
| 1. wasm_loader.js   | ----> | testProxyWasm(url)    |      |                           |
| 2. Promise Creation | <---- | Returns JS Promise    |      |                           |
| 3. await Promise    |       |                       |      |                           |
|                     |       | doTestProxy()         |      |                           |
| 4. JS WebSocket API | <---- | js.Global().Get("WS") | ---> | wss:// Proxy Server       |
| 5. onOpen / onError | ----> | js.FuncOf() Callbacks | <--- | Connection Success / Fail |
| 6. resolve()        | <---- | Promise resolve.Invoke|      |                           |
+---------------------+       +-----------------------+      +---------------------------+
```

## 2. Memory Safety & Garbage Collection Audit Findings
- **JS.Func Leaks Avoided (Mostly):** The Go implementation correctly uses `defer onOpen.Release()` and `defer onError.Release()` for the WebSocket event handlers. The Promise handler itself is properly released immediately after creation (`handler.Release()`) since it is executed synchronously by the `new Promise()` constructor.
- **Critical Risk (Race Condition & Panic):** In `doTestProxy`, if the 5-second timeout is reached, the function returns and triggers the deferred `Release()` calls for `onOpen` and `onError`. However, calling `jsWS.Call("close")` might still trigger a deferred `onerror` event asynchronously in the JS engine. If the JS engine invokes a released `js.Func`, it will cause a fatal WebAssembly panic and crash the Go runtime.
  - *Recommendation:* Explicitly remove the JS event listeners (`jsWS.Set("onopen", js.Null())`, etc.) before releasing the Go functions.
- **Batch Processing Limits:** `wasm_loader.js` splits proxy tests into chunks of 10 (`CHUNK_SIZE`). This limits concurrent WebSocket allocations, preventing memory pressure and excessive file descriptor usage within the browser.

## 3. Browser Networking Capability & Limitation Matrix
| Capability | Status | Notes |
|------------|--------|-------|
| HTTP(S) Requests | ✅ Supported | Full support via `fetch` API. |
| WebSockets (WS/WSS) | ✅ Supported | Full support via browser `WebSocket` object. |
| Raw TCP Sockets | ❌ Blocked | Browsers do not expose raw TCP sockets. Proxies relying solely on TCP handshakes cannot be tested directly. |
| Raw UDP Sockets | ❌ Blocked | No browser API for arbitrary UDP. |
| Vmess / Vless / etc. | ⚠️ Emulated | The Go module maps these schemes to WSS to test basic reachability of the underlying server. |

## 4. DOM & JS Global Namespace Isolation
- **Global Pollution:** Both the Go code and JS loader pollute the global `window` object with variables like `testProxyWasm`, `cleanupWasm`, `wasmReady`, `wasmError`, and `verifyProxyBatch`.
- **Recommendation:** Scope all WASM interop variables and functions under a single dedicated namespace object like `window.ConfigStream.WASM` to prevent collisions with other scripts or proxy UI components.

## 5. Error Boundary & Exception Handling Assessment
- **Go Panics:** The `doTestProxy` function has a `defer func() { recover() }()` block. However, if a panicked goroutine does not properly resolve the JS Promise, the JS `await` in `verifyProxyBatch` might hang indefinitely.
- **JS Loading Fallbacks:** `wasm_loader.js` robustly wraps initialization in a `try/catch` and sets `wasmReady = false`. `verifyProxyBatch` correctly checks this flag and smoothly falls back to server-side latency measurements.
- **Missing Reject Call:** The Promise handler in Go only captures `resolve` and does not invoke `reject` when an error happens. While it returns an object with an `error` field, native JS try-catch blocks won't catch it unless they inspect `res.error`.

## 6. Code Optimization Recommendations
1. **Nullify Callbacks Before Release:** Add `jsWS.Set("onopen", js.Null())` and `jsWS.Set("onerror", js.Null())` inside a defer block before `Release()` is called to prevent panics.
2. **Implement Reject:** Extract `reject = promiseArgs[1]` in Go and use it to throw actual JS errors from the WASM module when a panic or critical validation failure occurs.
3. **Promise Resolution Guarantee:** Ensure the Promise is always resolved or rejected within the `recover()` block to prevent JS hanging.
4. **Namespace Isolation:** Move all global bindings into an isolated `ConfigStream.WASM` object.
