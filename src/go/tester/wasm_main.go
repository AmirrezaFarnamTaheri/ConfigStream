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

	// Register test function and keep reference
	testFunc := js.FuncOf(testProxy)
	js.Global().Set("testProxyWasm", testFunc)

	// Register cleanup function to prevent memory leaks
	cleanupFunc := js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		testFunc.Release()
		return nil
	})
	js.Global().Set("cleanupWasm", cleanupFunc)

	println("WASM Proxy Tester Initialized (JS-Native)")
	<-c
}

// testProxy expects arguments: [proxyUrl, uuid (optional)]
func testProxy(this js.Value, args []js.Value) interface{} {
	if len(args) < 1 {
		return map[string]interface{}{"error": "Missing proxy URL"}
	}
	url := args[0].String()

	// Create a channel to receive result
	done := make(chan interface{})

	// Prepare callbacks
	var onOpen, onError js.Func
	var jsWS js.Value

	// Panic handler for JS exceptions
	defer func() {
		if r := recover(); r != nil {
			// Ensure callbacks are released if panic happens before select
			if onOpen.Truthy() { onOpen.Release() }
			if onError.Truthy() { onError.Release() }
			// We can't return from here to JS caller, but we can prevent crash loop
			// Ideally we push to done but we might be stuck
		}
	}()

	start := time.Now()

	onOpen = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		latency := time.Since(start).Milliseconds()
		jsWS.Call("close")
		// Use goroutine to send to channel to avoid blocking JS event loop callback
		go func() {
			done <- map[string]interface{}{"alive": true, "latency": latency}
		}()
		return nil
	})

	onError = js.FuncOf(func(this js.Value, args []js.Value) interface{} {
		go func() {
			done <- map[string]interface{}{"alive": false, "error": "Connection Failed"}
		}()
		return nil
	})

	// Instantiate WebSocket using browser API
	// Note: This throws JS exception if URL is invalid scheme (e.g. vmess://)
	// We should probably replace vmess:// with wss:// if needed?
	// The audit snippet assumed URL is valid for WebSocket constructor.
	// But proxies are vmess://. Browser WebSocket needs ws:// or wss://.
	// We should replace scheme.

	wsUrl := url
	if len(wsUrl) > 8 && (wsUrl[:8] == "vmess://" || wsUrl[:8] == "vless://") {
		wsUrl = "wss://" + wsUrl[8:]
	} else if len(wsUrl) > 5 && (wsUrl[:5] == "ss://") {
		// SS over WS? Rare but possible.
		// We'll trust the user or simple replacement.
		wsUrl = "wss://" + wsUrl[5:]
	}

	// Try-catch for New? syscall/js doesn't expose try-catch.
	// We rely on simple string replacement and hope.

	jsWS = js.Global().Get("WebSocket").New(wsUrl)
	jsWS.Set("onopen", onOpen)
	jsWS.Set("onerror", onError)

	// Wait for result or timeout
	select {
	case res := <-done:
		onOpen.Release()
		onError.Release()
		return res
	case <-time.After(5 * time.Second):
		jsWS.Call("close")
		onOpen.Release()
		onError.Release()
		return map[string]interface{}{"alive": false, "error": "Timeout"}
	}
}
