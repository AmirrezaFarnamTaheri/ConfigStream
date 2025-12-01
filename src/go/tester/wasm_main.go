//go:build js && wasm
// +build js,wasm

package main

import (
	"fmt"
	"net/http"
	"strings"
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

	// [FIX] Detect non-WS protocols and warn user
	// In a browser environment, we can't make raw TCP connections.
	if !strings.Contains(proxyUrl, "ws") && !strings.Contains(proxyUrl, "http") {
		return map[string]interface{}{
			"alive": false,
			"error": "WASM Limitation: Browser can only test WebSocket/HTTP transports. TCP/UDP proxies require backend testing.",
		}
	}

	// Default to a websocket test
	// We can only test WebSocket-based proxies (VLESS-ws, VMess-ws, etc.)
	// or perform a simple HTTP fetch if the proxy exposes an HTTP endpoint (unlikely for raw proxies).

	// NOTE: The browser enforces CORS. Connecting to a random VLESS-ws endpoint
	// may fail if the server doesn't send Access-Control-Allow-Origin.
	// However, for WebSocket, the Same-Origin Policy is more relaxed,
	// but the server must still accept the connection.

	start := time.Now()

	// Attempt WebSocket Dial
	dialer := websocket.Dialer{
		HandshakeTimeout: 5 * time.Second,
	}

	// Helper: Ensure scheme is websocket compatible
	targetUrl := proxyUrl
	if strings.HasPrefix(targetUrl, "vless://") || strings.HasPrefix(targetUrl, "vmess://") {
		// Assuming conversion logic happens in JS before calling this or valid WS URL is passed
		// But as a fallback, replace scheme if it looks like a standard URL structure
		targetUrl = strings.Replace(targetUrl, "vless://", "wss://", 1)
		targetUrl = strings.Replace(targetUrl, "vmess://", "wss://", 1)
	}

	conn, _, err := dialer.Dial(targetUrl, http.Header{})
	if err != nil {
		// Classify error type for better debugging
		errType := "UNKNOWN"
		errMsg := err.Error()

		// Check for common error patterns
		if websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
			errType = "CONNECTION_CLOSED"
		} else if websocket.IsUnexpectedCloseError(err) {
			errType = "UNEXPECTED_CLOSE"
		} else {
			// String matching for other error types
			switch {
			case len(errMsg) > 0 && errMsg[0:7] == "timeout":
				errType = "TIMEOUT"
			case len(errMsg) > 0 && errMsg[0:10] == "connection":
				errType = "CONNECTION_REFUSED"
			default:
				errType = "DIAL_FAILED"
			}
		}

		return map[string]interface{}{
			"alive":     false,
			"error":     errMsg,
			"error_type": errType,
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
