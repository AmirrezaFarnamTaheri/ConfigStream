//go:build js && wasm

package main

import (
	"syscall/js"
	"time"
	"net/http"
)

var validPromise = js.Global().Get("Promise")

func checkProxy(this js.Value, args []js.Value) interface{} {
    // 1. Parse Arguments
	proxyURL := args[0].String()

    // 2. Define Handler
	handler := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		resolve := args[0]
		// reject := args[1]

		go func() {
            // 3. Perform Test (Timing Attack / Fetch)
			start := time.Now()

            // Note: In WASM, http.Client uses the browser's fetch API.
            // It will fail for many cross-origin requests unless the target supports CORS.
            // However, this serves as a basic connectivity check for standard targets
            // or proxies that are properly configured (or if we are checking the proxy server itself).

            // For true VLESS handshake, we need a WebSocket bridge, which is more complex.
            // This implementation matches the "Scanner" requirement: Basic reachability.

            client := http.Client{Timeout: 5 * time.Second}
			_, err := client.Head(proxyURL)

            latency := time.Since(start).Milliseconds()

            alive := err == nil

            // If failed, latency is max
            if !alive {
                latency = 9999
            }

            result := map[string]interface{}{
				"alive":   alive,
				"latency": latency,
			}

			resolve.Invoke(js.ValueOf(result))
		}()
		return nil
	})

	return validPromise.New(handler)
}

func main() {
	c := make(chan struct{}, 0)
	js.Global().Set("testProxyWasm", js.FuncOf(checkProxy))
	<-c
}
