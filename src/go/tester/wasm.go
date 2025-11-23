// +build wasm

package main

import (
	"syscall/js"
)

// This file implements the WASM interface for client-side testing.
// It will be compiled when GOOS=js and GOARCH=wasm.

func checkProxyWasm(this js.Value, args []js.Value) interface{} {
	if len(args) < 1 {
		return map[string]interface{}{"success": false, "error": "Missing config argument"}
	}

	configStr := args[0].String()

	// In a real WASM implementation, we would:
	// 1. Parse the configStr
	// 2. Create a Sing-box instance (if compatible with WASM) OR
	// 3. Use a simplified HTTP/WebSocket check logic compatible with browser sandbox

	// Since standard Sing-box relies on raw sockets which browsers block,
	// we implement a basic "connectivity check" simulation or use WebSocket relay logic here.

	// Placeholder logic for the 'Zero to Hero' WASM demo:
	// We return a success since we can't easily bind raw sockets in the browser without a relay.
	// Real implementation would use a WebSocket-based transport or HTTP Connect via relay.

	return map[string]interface{}{
		"success": true,
		"latency": 100, // Mock latency
		"message": "WASM Check Passed (Simulation: " + configStr[0:10] + "...) - Browser limitation requires Relay for full TCP",
	}
}

func main() {
	c := make(chan struct{}, 0)
	js.Global().Set("checkProxy", js.FuncOf(checkProxyWasm))
	<-c
}
