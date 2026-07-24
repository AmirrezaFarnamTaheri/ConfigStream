// SPDX-License-Identifier: AGPL-3.0-or-later
//go:build js && wasm
// +build js,wasm

package main

import (
	"net/url"
	"strings"
	"syscall/js"
	"time"
)

func main() {
	// Idiomatic unbuffered channel (removed redundant ", 0")
	c := make(chan struct{})

	// Register test function and keep reference
	testFunc := js.FuncOf(testProxyWasm)
	js.Global().Set("testProxyWasm", testFunc)

	// Register cleanup function that also releases itself to prevent memory leak
	var cleanupFunc js.Func
	cleanupFunc = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		testFunc.Release()
		cleanupFunc.Release()
		return nil
	})
	js.Global().Set("cleanupWasm", cleanupFunc)

	println("WASM Browser Reachability Tester Initialized")
	<-c
}

// testProxyWasm expects arguments: [proxyUrl, uuid (optional)]
// Returns a JavaScript Promise instead of blocking the JS event loop.
// Previously, the select{} blocked the Go goroutine for up to 5 seconds,
// which froze the entire WASM runtime and the calling JS thread.
func testProxyWasm(this js.Value, args []js.Value) interface{} {
	if len(args) < 1 {
		return js.ValueOf(map[string]interface{}{"error": "Missing proxy URL"})
	}
	rawURL := args[0].String()

	// Create and return a JavaScript Promise
	handler := js.FuncOf(func(this js.Value, promiseArgs []js.Value) interface{} {
		resolve := promiseArgs[0]
		reject := promiseArgs[1]

		go func() {
			defer func() {
				if r := recover(); r != nil {
					reject.Invoke(js.ValueOf(map[string]interface{}{
						"alive": false,
						"error": "WASM execution panic",
					}))
				}
			}()
			result := doTestProxy(rawURL)
			resolve.Invoke(js.ValueOf(result))
		}()

		return nil
	})

	promise := js.Global().Get("Promise").New(handler)
	handler.Release()
	return promise
}

func doTestProxy(rawURL string) map[string]interface{} {

	start := time.Now()

	wsURL, unsupported := normalizeBrowserReachabilityURL(rawURL)
	if unsupported != "" {
		return map[string]interface{}{
			"alive": false,
			"error": unsupported,
		}
	}

	// Create channels for async result
	done := make(chan map[string]interface{}, 1)

	var onOpen, onError js.Func
	var jsWS js.Value

	sendResult := func(res map[string]interface{}) {
		select {
		case done <- res:
		default:
		}
	}

	onOpen = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		latency := time.Since(start).Milliseconds()
		if !jsWS.IsUndefined() && !jsWS.IsNull() {
			jsWS.Call("close")
		}
		sendResult(map[string]interface{}{"alive": true, "latency": latency})
		return nil
	})

	onError = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		sendResult(map[string]interface{}{"alive": false, "error": "Connection Failed"})
		return nil
	})

	defer func() {
		if !jsWS.IsUndefined() && !jsWS.IsNull() {
			jsWS.Set("onopen", js.Null())
			jsWS.Set("onerror", js.Null())
		}
		onOpen.Release()
		onError.Release()
	}()

	jsWS = js.Global().Get("WebSocket").New(wsURL)
	jsWS.Set("onopen", onOpen)
	jsWS.Set("onerror", onError)

	// Wait for result or timeout
	select {
	case res := <-done:
		return res
	case <-time.After(5 * time.Second):
		if !jsWS.IsUndefined() && !jsWS.IsNull() {
			jsWS.Call("close")
		}
		return map[string]interface{}{"alive": false, "error": "Timeout"}
	}
}

func normalizeBrowserReachabilityURL(rawURL string) (string, string) {
	rawURL = strings.TrimSpace(rawURL)
	if rawURL == "" {
		return "", "Invalid URL"
	}

	lowerURL := strings.ToLower(rawURL)
	if strings.HasPrefix(lowerURL, "ws://") || strings.HasPrefix(lowerURL, "wss://") {
		return validateBrowserURL(rawURL)
	}

	knownProxySchemes := []string{
		"vmess://", "vless://", "trojan://", "hysteria://",
		"hysteria2://", "hy2://", "hysteria3://", "hy3://", "tuic://", "ssr://", "ss://",
	}
	for _, scheme := range knownProxySchemes {
		if strings.HasPrefix(lowerURL, scheme) {
			return validateBrowserURL("wss://" + rawURL[len(scheme):])
		}
	}

	return "", "Unsupported browser reachability scheme"
}

func validateBrowserURL(candidate string) (string, string) {
	parsed, err := url.Parse(candidate)
	if err != nil || parsed.Host == "" {
		return "", "Invalid URL"
	}
	if parsed.Scheme != "ws" && parsed.Scheme != "wss" {
		return "", "Unsupported browser reachability scheme"
	}
	return candidate, ""
}
