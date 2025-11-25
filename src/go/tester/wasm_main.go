//go:build js && wasm
// +build js,wasm

package main

import (
	"fmt"
	"net/http"
	"syscall/js"
	"time"

	"github.com/gorilla/websocket"
)

func main() {
	c := make(chan struct{}, 0)
	js.Global().Set("testProxyWasm", js.FuncOf(testProxy))
	fmt.Println("WASM Proxy Tester Initialized")
	<-c
}

// testProxy expects arguments: [proxyUrl, uuid (optional)]
func testProxy(this js.Value, args []js.Value) interface{} {
	if len(args) < 1 {
		return map[string]interface{}{"error": "Missing proxy URL"}
	}
	proxyUrl := args[0].String()

	// Default to a websocket test
	// In a browser environment, we can't make raw TCP connections.
	// We can only test WebSocket-based proxies (VLESS-ws, VMess-ws, etc.)
	// or perform a simple HTTP fetch if the proxy exposes an HTTP endpoint (unlikely for raw proxies).

	// NOTE: The browser enforces CORS. Connecting to a random VLESS-ws endpoint
	// might fail if the server doesn't send Access-Control-Allow-Origin.
	// However, for WebSocket, the Same-Origin Policy is more relaxed,
	// but the server must still accept the connection.

	start := time.Now()

	// Attempt WebSocket Dial
	dialer := websocket.Dialer{
		HandshakeTimeout: 5 * time.Second,
	}

	// We might need to transform the custom scheme (vless://) to ws:// or wss://
	// Ideally the input should be the actual WebSocket endpoint URL.
	// For this PoC, we assume the input is "wss://host:port/path"

	conn, _, err := dialer.Dial(proxyUrl, http.Header{})
	if err != nil {
		return map[string]interface{}{
			"alive": false,
			"error": err.Error(),
		}
	}
	defer conn.Close()

	// If connected, we consider it "alive" for Layer 4 (TCP/WS established).
	// For Layer 5 (VLESS), we would need to send a handshake.

	latency := time.Since(start).Milliseconds()

	return map[string]interface{}{
		"alive":   true,
		"latency": latency,
	}
}
