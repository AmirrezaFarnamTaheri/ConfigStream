// +build wasm

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"syscall/js"
	"time"

	"nhooyr.io/websocket"
)

// This file implements the WASM interface for client-side testing.
// It will be compiled when GOOS=js and GOARCH=wasm.
//
// Browser Limitation: We CANNOT open raw TCP sockets.
// Solution: We can ONLY test proxies that use WebSocket transport (vmess+ws, vless+ws, trojan+ws).
// For others, we return a "Not Supported in Browser" message.

// Wrapper to create a JS Promise
func newPromise(handler js.Func) js.Value {
	promiseConstructor := js.Global().Get("Promise")
	return promiseConstructor.New(handler)
}

// Actual test function exposed
func testProxy(this js.Value, args []js.Value) interface{} {
	if len(args) < 1 {
		return map[string]interface{}{"success": false, "error": "Missing config"}
	}

    // We expect a JSON string of the proxy object
	proxyJSON := args[0].String()

	handler := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		resolve := args[0]

		go func() {
            start := time.Now()

            // 1. Unmarshal
            var p map[string]interface{}
            if err := json.Unmarshal([]byte(proxyJSON), &p); err != nil {
                resolve.Invoke(map[string]interface{}{"success": false, "error": "JSON Parse Error"})
                return
            }

            details, _ := p["details"].(map[string]interface{})
            netType, _ := details["net"].(string)
            path, _ := details["path"].(string)

            // Handle number conversion safely
            portFloat, ok := p["port"].(float64)
            if !ok {
                 resolve.Invoke(map[string]interface{}{"success": false, "error": "Invalid Port"})
                 return
            }
            port := int(portFloat)

            addr, _ := p["address"].(string)
            tls, _ := details["tls"].(string)

            // 2. Browser Sandbox Check
            // We can ONLY test WebSockets.
            if netType != "ws" {
                resolve.Invoke(map[string]interface{}{
                    "success": false,
                    "error": "Browser Limitation: Can only test WebSocket (ws) proxies.",
                    "skipped": true,
                })
                return
            }

            // 3. Construct WebSocket URL
            scheme := "ws"
            if tls == "tls" {
                scheme = "wss"
            }

            // If path is missing, default to /
            if path == "" {
                path = "/"
            }

            url := fmt.Sprintf("%s://%s:%d%s", scheme, addr, port, path)

            // 4. Test Connection
            // We use nhooyr.io/websocket or just standard context
            ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
            defer cancel()

            // In WASM, this uses the browser's WebSocket API under the hood
            c, _, err := websocket.Dial(ctx, url, nil)
            if err != nil {
                 resolve.Invoke(map[string]interface{}{
                    "success": false,
                    "error": fmt.Sprintf("Connection Failed: %v", err),
                })
                return
            }
            defer c.Close(websocket.StatusNormalClosure, "bye")

            // If we connected, calculate latency
            latency := time.Since(start).Milliseconds()

            resolve.Invoke(map[string]interface{}{
                "success": true,
                "latency": latency,
                "message": fmt.Sprintf("Connected to %s in %dms", url, latency),
            })
		}()
		return nil
	})

	return newPromise(handler)
}


func main() {
	c := make(chan struct{}, 0)
	js.Global().Set("checkProxy", js.FuncOf(testProxy))
	<-c
}
