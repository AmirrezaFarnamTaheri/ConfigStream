# Known Issues and Limitations

## 1. Go WASM Networking Limitation (Critical Architectural Issue)

### Status: Known Limitation - Requires Architectural Redesign

**Issue:** The current Go WASM implementation (`src/go/tester/wasm_main.go`) attempts to use Go's standard networking libraries (e.g., `github.com/gorilla/websocket`, `net.Dial`) which rely on TCP sockets.

**Root Cause:** Browser security sandboxes **block** direct TCP/UDP socket access from WebAssembly. WASM code can only access network resources through JavaScript APIs provided by the browser (e.g., `fetch`, `WebSocket`, `XMLHttpRequest`).

**Impact:**
- WASM-based proxy testing in the browser will fail
- All proxies tested through WASM will show as "Network Error" or `latency: 9999`
- The "Turbo-Verify (Local)" feature is non-functional in its current state

**Workaround:**
The backend Go tester (`configstream-tester` binary) still functions correctly for server-side testing. Frontend proxy verification should rely on backend API calls rather than client-side WASM testing.

**Proper Fix (Requires Significant Refactoring):**
Rewrite `src/go/tester/wasm_main.go` to use `syscall/js` bindings to invoke browser's native JavaScript APIs:

```go
package main

import (
    "syscall/js"
    "time"
)

func testProxy(this js.Value, args []js.Value) interface{} {
    url := args[0].String()
    done := make(chan interface{})

    // Use JavaScript's WebSocket API via syscall/js
    jsWS := js.Global().Get("WebSocket").New(url)

    start := time.Now()

    onOpen := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        latency := time.Since(start).Milliseconds()
        jsWS.Call("close")
        done <- map[string]interface{}{"alive": true, "latency": latency}
        return nil
    })

    onError := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
        done <- map[string]interface{}{"alive": false, "error": "Connection Failed"}
        return nil
    })

    jsWS.Set("onopen", onOpen)
    jsWS.Set("onerror", onError)

    select {
    case res := <-done:
        return res
    case <-time.After(5 * time.Second):
        jsWS.Call("close")
        return map[string]interface{}{"alive": false, "error": "Timeout"}
    }
}

func main() {
    js.Global().Set("testProxyWasm", js.FuncOf(testProxy))
    <-make(chan bool) // Keep WASM alive
}
```

**Recommended Approach:**
1. **Short-term:** Disable or remove WASM-based testing from the frontend
2. **Long-term:** Implement proper `syscall/js` bindings or use a pure JavaScript implementation for client-side testing
3. **Alternative:** Use WebRTC Data Channels which provide broader network access (but still limited to specific protocols)

---

## 2. Mobile Layout Considerations

**Status:** Minor - Already Mitigated

The CSS includes comprehensive mobile responsive design with:
- `overflow-x: hidden` on all container elements
- Proper z-index hierarchy for mobile navigation
- Responsive grid layouts that adapt to screen size
- Touch-friendly target sizes

**Note:** The z-index mobile menu issue reported in early analysis has been **fixed** (header: 1000, nav-panel: 1005).

---

## 3. Country Flag Asset Dependency

**Status:** Low Priority

The frontend relies on `flagcdn.com` for country flag images. If this external service is unavailable:
- Flags will not load (broken image icons)
- Fallback to Feather "globe" icon is in place

**Mitigation:** Consider bundling flag SVGs locally or using a fallback sprite sheet.

---

## 4. Vwarp and Chain Statistics Display

**Status:** Fixed in Latest Commit

Previously, `smart_chain_count` and `vwarp_win_rate` were tracked in the backend but not displayed in the frontend.

**Resolution:** Added two new statistics cards to the dashboard:
- **Smart Chains:** Displays the count of topology-aware chains created
- **Vwarp Efficiency:** Shows the win rate percentage for WARP washing attempts

These statistics are now visible on the main dashboard and update with each pipeline cycle.

---

## 5. MIME Type Handling for WASM

**Status:** Fixed

Browsers require `.wasm` files to be served with `Content-Type: application/wasm`. This has been explicitly configured in `server.py`:

```python
mimetypes.add_type("application/wasm", ".wasm")
```

This ensures the FastAPI static file server serves WASM files with the correct MIME type.

---

## Contributing

If you can help address any of these issues, particularly the Go WASM networking limitation, please submit a pull request or open an issue for discussion.
