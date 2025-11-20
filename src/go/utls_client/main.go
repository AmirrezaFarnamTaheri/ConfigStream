package main

import (
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"time"

	tls "github.com/refraction-networking/utls"
)

// Simple uTLS client to verify connectivity and fingerprint randomization
// This is a basic implementation. In a real scenario, we would use this to fetch a test URL via the proxy.
// For Phase 4, we focus on the TLS handshake part.

func main() {
	targetUrl := flag.String("url", "https://www.google.com", "Target URL to fetch")
	proxyAddr := flag.String("proxy", "", "Proxy address (host:port) - currently supports direct connection for testing")
	fingerprint := flag.String("fp", "chrome", "Fingerprint ID (chrome, firefox, ios, random)")
	flag.Parse()

	if *targetUrl == "" {
		fmt.Println("Error: URL is required")
		os.Exit(1)
	}

	// Parse URL
	// For simplicity in this "Zero Budget" proof-of-concept, we implement a direct TLS handshake
	// to the target (or via proxy if we added SOCKS5 support, but let's keep it simple first).
    // Note: To properly route through a proxy using Go, we'd need a SOCKS/HTTP dialer.
    // Given the constraints, we will demonstrate uTLS connectivity directly to the target
    // to prove the fingerprinting capability. The Python fetcher handles the actual proxy routing
    // but if we want to test if the *proxy* passes the fingerprint, we need to tunnel through it.
    // For now, let's assume we are testing the connection logic itself.

	dialer := &net.Dialer{
		Timeout: 10 * time.Second,
	}

    // Mock connection setup
	conn, err := dialer.Dial("tcp", "www.google.com:443") // Hardcoded for PoC, normally parse *targetUrl
	if err != nil {
		fmt.Printf("Failed to dial: %v\n", err)
		os.Exit(1)
	}

    // Determine Hello ID
    var helloID tls.ClientHelloID
    switch *fingerprint {
    case "chrome":
        helloID = tls.HelloChrome_Auto
    case "firefox":
        helloID = tls.HelloFirefox_Auto
    case "ios":
        helloID = tls.HelloIOS_Auto
    case "random":
        helloID = tls.HelloRandomized
    default:
        helloID = tls.HelloChrome_Auto
    }

	uConn := tls.UClient(conn, &tls.Config{
		ServerName: "www.google.com",
        InsecureSkipVerify: true,
	}, helloID)

	err = uConn.Handshake()
	if err != nil {
		fmt.Printf("Handshake failed: %v\n", err)
		os.Exit(1)
	}

    // Send HTTP GET
	_, err = uConn.Write([]byte("GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n"))
	if err != nil {
		fmt.Printf("Write failed: %v\n", err)
		os.Exit(1)
	}

	buf := make([]byte, 1024)
	n, err := uConn.Read(buf)
	if err != nil && err != io.EOF {
		fmt.Printf("Read failed: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Success: %d bytes received using %s fingerprint\n", n, *fingerprint)
}
