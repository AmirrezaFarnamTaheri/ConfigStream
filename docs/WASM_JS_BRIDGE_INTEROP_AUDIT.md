# WASM JS Bridge Interop & Browser Bounds Audit

## 1. WASM JS Bridge Interop Architecture Diagram

```ascii
+-----------------------+                    +------------------------+
|   Browser JS Engine   |                    |    Go WASM Runtime     |
|                       |                    |                        |
|  [Global Namespace]   |                    |                        |
|  - testProxyWasm()  <-------- Invoke --------- testProxyWasm()      |
|  - cleanupWasm()    <-------- Invoke --------- cleanupFunc()        |
|                       |                    |                        |
|  [Promise Creation]   |                    |                        |
|  - new Promise()    -------- Callback -------> go func() goroutine  |
|                       |                    |                        |
|  [Network Bounds]     |                    |                        |
|  - WebSocket API    <------- WSS Auth -------- doTestProxy()        |
+-----------------------+                    +------------------------+
```

## 2. Go Panic Recovery & Promise Rejection Audit

| Category | Finding | Status |
|---|---|---|
| **Promise Resolution** | The async goroutine returns a Promise to avoid blocking the JS event loop. | ✅ Pass |
| **Panic Handling** | `doTestProxy` uses `defer func() { recover() }()` but fails to pass the error to JS. | ❌ Fail |
| **Promise Rejection** | If a panic occurs, the Promise is resolved with a zero-value (null/undefined) instead of being explicitly rejected via the `reject` callback. | ❌ Fail |

**Issue:** 
The `testProxyWasm` function creates a Promise but ignores the `reject` parameter. When `doTestProxy` panics, the deferred recover block catches it, but the goroutine continues and evaluates `resolve.Invoke(js.ValueOf(result))` with a zero-value `result` (nil map). This leads to the Promise resolving with empty data instead of properly rejecting.

## 3. Memory Allocation & Garbage Collection Benchmark

- `js.FuncOf` Callbacks: `testFunc` and `cleanupFunc` are explicitly released inside `cleanupWasm`.
- Promise Handler: `handler.Release()` is immediately called after Promise instantiation.
- WebSocket Events: `onOpen` and `onError` are tracked and cleanly released via `defer onOpen.Release()` and `defer onError.Release()`.
- **Verdict**: Memory management is handled correctly for `js.Func`, averting memory leaks across repeated JS calls. 

## 4. Namespace Encapsulation & Global Scope Isolation

**Issue:** 
The Go side binds WASM exports directly to `js.Global()` (`testProxyWasm` and `cleanupWasm`), polluting the global window object.

**Finding:**
It does not encapsulate these methods inside a dedicated `ConfigStream.WASM` namespace as required by the architecture specification.

## 5. Browser-Limited Network Boundaries

- Browser socket APIs are correctly respected. 
- Go does not attempt to instantiate raw TCP/UDP connections.
- The `normalizeBrowserReachabilityURL` rewrites custom proxy protocols (`vmess://`, `vless://`, etc.) strictly to `wss://`, enforcing emulated WSS connections over browser WebSocket implementations.

## Recommended Code Patches

**1. Fix Promise Rejection and Panic Handling (`wasm_main.go`)**
```go
func testProxyWasm(this js.Value, args []js.Value) interface{} {
    // ...
    handler := js.FuncOf(func(this js.Value, promiseArgs []js.Value) interface{} {
        resolve := promiseArgs[0]
        reject := promiseArgs[1]

        go func() {
            defer func() {
                if r := recover(); r != nil {
                    reject.Invoke(js.ValueOf(map[string]interface{}{"error": "Internal WASM Panic"}))
                }
            }()
            result := doTestProxy(rawURL)
            resolve.Invoke(js.ValueOf(result))
        }()
        return nil
    })
    // ...
}
```
*(Note: Remove the `recover()` from `doTestProxy` and handle it in the wrapping goroutine).*

**2. Namespace Encapsulation (`wasm_main.go`)**
```go
// Ensure namespace exists
if js.Global().Get("ConfigStream").IsUndefined() {
    js.Global().Set("ConfigStream", map[string]interface{}{})
}
if js.Global().Get("ConfigStream").Get("WASM").IsUndefined() {
    js.Global().Get("ConfigStream").Set("WASM", map[string]interface{}{})
}

// Bind to namespace
wasmSpace := js.Global().Get("ConfigStream").Get("WASM")
wasmSpace.Set("testProxyWasm", testFunc)
wasmSpace.Set("cleanupWasm", cleanupFunc)
```
