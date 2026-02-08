// SPDX-License-Identifier: AGPL-3.0-or-later
//go:build js && wasm
// +build js,wasm

package main

import (
	"syscall/js"
	"time"
)

func main() {
	c := make(chan struct{}, 0)
	js.Global().Set("testProxyWasm", js.FuncOf(testProxyAsync))
	println("WASM Proxy Tester Initialized (JS-Native Async)")
	<-c
}

func testProxyAsync(this js.Value, args []js.Value) interface{} {
	if len(args) < 1 {
		return nil
	}
	url := args[0].String()

	// Return a Promise
	handler := js.FuncOf(func(this js.Value, pArgs []js.Value) interface{} {
		resolve := pArgs[0]

		// Helper to safely invoke resolve
		safeResolve := func(alive bool, latency int64, errStr string) {
			res := make(map[string]interface{})
			res["alive"] = alive
			if alive {
				res["latency"] = latency
			} else {
				res["error"] = errStr
			}
			resolve.Invoke(js.ValueOf(res))
		}

		go func() {
			// Protocol adjustment
			wsUrl := url
			if len(wsUrl) > 8 && (wsUrl[:8] == "vmess://" || wsUrl[:8] == "vless://") {
				wsUrl = "wss://" + wsUrl[8:]
			} else if len(wsUrl) > 5 && (wsUrl[:5] == "ss://") {
				wsUrl = "wss://" + wsUrl[5:]
			}

			// We use channels to coordinate
			resultCh := make(chan map[string]interface{})

			var jsWS js.Value
			var onOpen, onError js.Func

			// Cleanup function
			cleanup := func() {
				// Check Truthy before Release to avoid panic if not initialized
				if onOpen.Truthy() { onOpen.Release() }
				if onError.Truthy() { onError.Release() }
				if jsWS.Truthy() { jsWS.Call("close") }
			}

			start := time.Now()

			onOpen = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
				latency := time.Since(start).Milliseconds()
				// Send non-blocking or ensure receiver is ready
				select {
				case resultCh <- map[string]interface{}{"alive": true, "latency": latency}:
				default:
				}
				return nil
			})

			onError = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
				select {
				case resultCh <- map[string]interface{}{"alive": false, "error": "Connection Failed"}:
				default:
				}
				return nil
			})

			// Initialize WebSocket
			// This might throw if URL is invalid
			defer func() {
				if r := recover(); r != nil {
					// safeResolve(false, 0, "Invalid URL")
					// We can't resolve from here if main goroutine is blocked on select
					// But we are in the goroutine.
					// Just send to channel
					select {
					case resultCh <- map[string]interface{}{"alive": false, "error": "Invalid URL"}:
					default:
					}
				}
			}()

			jsWS = js.Global().Get("WebSocket").New(wsUrl)
			jsWS.Set("onopen", onOpen)
			jsWS.Set("onerror", onError)

			// Wait for result or timeout
			select {
			case res := <-resultCh:
				cleanup()
				alive := res["alive"].(bool)
				if alive {
					safeResolve(true, res["latency"].(int64), "")
				} else {
					safeResolve(false, 0, res["error"].(string))
				}
			case <-time.After(5 * time.Second):
				cleanup()
				safeResolve(false, 0, "Timeout")
			}
		}()

		return nil
	})

	return js.Global().Get("Promise").New(handler)
}
