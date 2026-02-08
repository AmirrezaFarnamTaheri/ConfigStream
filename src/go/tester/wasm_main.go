// SPDX-License-Identifier: AGPL-3.0-or-later
//go:build js && wasm
// +build js,wasm

package main

import (
	"strings"
	"syscall/js"
	"time"
)

func main() {
	// [FIX] Idiomatic unbuffered channel (removed redundant ", 0")
	c := make(chan struct{})

	// Register test function and keep reference
	testFunc := js.FuncOf(testProxyWasm)
	js.Global().Set("testProxyWasm", testFunc)

	// [FIX] Register cleanup function that also releases itself to prevent memory leak
	var cleanupFunc js.Func
	cleanupFunc = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		testFunc.Release()
		cleanupFunc.Release()
		return nil
	})
	js.Global().Set("cleanupWasm", cleanupFunc)

	println("WASM Proxy Tester Initialized (JS-Native)")
	<-c
}

// testProxyWasm expects arguments: [proxyUrl, uuid (optional)]
// [FIX] Returns a JavaScript Promise instead of blocking the JS event loop.
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
		// reject := promiseArgs[1] // available if needed

		go func() {
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
	// Panic handler for JS exceptions
	defer func() {
		if r := recover(); r != nil {
			// Can't return from here, but prevent crash loop
		}
	}()

	start := time.Now()

	// [FIX] Handle all known proxy protocol schemes, not just vmess/vless/ss.
	// Previously, trojan://, hysteria://, etc. were passed directly to WebSocket.New()
	// which throws a JS exception.
	wsURL := rawURL
	knownSchemes := []string{
		"vmess://", "vless://", "trojan://", "hysteria://",
		"hysteria2://", "hy2://", "tuic://", "ssr://",
	}
	for _, scheme := range knownSchemes {
		if len(wsURL) >= len(scheme) && strings.EqualFold(wsURL[:len(scheme)], scheme) {
			wsURL = "wss://" + wsURL[len(scheme):]
			break
		}
	}
	if len(wsURL) > 5 && wsURL[:5] == "ss://" {
		wsURL = "wss://" + wsURL[5:]
	}

	// Create channels for async result
	done := make(chan map[string]interface{}, 1)

	var onOpen, onError js.Func
	var jsWS js.Value

	onOpen = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		latency := time.Since(start).Milliseconds()
		jsWS.Call("close")
		done <- map[string]interface{}{"alive": true, "latency": latency}
		return nil
	})

	onError = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		done <- map[string]interface{}{"alive": false, "error": "Connection Failed"}
		return nil
	})

	defer onOpen.Release()
	defer onError.Release()

	jsWS = js.Global().Get("WebSocket").New(wsURL)
	jsWS.Set("onopen", onOpen)
	jsWS.Set("onerror", onError)

	// Wait for result or timeout
	select {
	case res := <-done:
		return res
	case <-time.After(5 * time.Second):
		jsWS.Call("close")
		return map[string]interface{}{"alive": false, "error": "Timeout"}
	}
}
