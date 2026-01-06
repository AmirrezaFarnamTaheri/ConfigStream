// SPDX-License-Identifier: AGPL-3.0-or-later
package main

import (
	"flag"
	"fmt"
	"io"
	"net"
	"os"
	"time"

	tls "github.com/refraction-networking/utls"
)

// Simple uTLS client to verify connectivity and fingerprint randomization
// This is a basic implementation. In a real scenario, we would use this to fetch a test URL via the proxy.
// For Phase 4, we focus on the TLS handshake part.

func main() {
	targetUrl := flag.String("url", "https://www.google.com", "Target URL to fetch")
	// Proxy address flag is deprecated/unused in this PoC but kept for interface compatibility
	_ = flag.String("proxy", "", "Proxy address (host:port) - currently supports direct connection for testing")
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
    // to prove the fingerprinting capability. The Python fetcher handles the actual proxy routing.
    // This proof-of-concept validates the uTLS handshake logic independently.

	dialer := &net.Dialer{
		Timeout: 10 * time.Second,
	}

    // Standard TCP connection setup
    // Dial the host extracted from the provided URL instead of a hard-coded one.
    parsed := *targetUrl
    host, port, err := net.SplitHostPort(parsed)
    if err != nil {
        // Fallback: if SplitHostPort fails, try to parse from url string or default to port 443
        // For simplicity in this fix, we assume input might be just host or host:port
        host = parsed
        port = "443"
        // If parsed is a full URL, we should parse it properly.
        // But for this patch, we follow the audit suggestion pattern.
    }

    // Better parsing logic to handle http:// prefix if present in *targetUrl
    // But audit patch just replaced the Dial line.
    // Let's be slightly more robust if possible, but stick to the patch spirit.

    // Using the patch logic:
    // host, port, err := net.SplitHostPort(parsed)
    // if err != nil { host = parsed; port = "443" }
    // conn, err := dialer.Dial("tcp", net.JoinHostPort(host, port))

    // However, *targetUrl defaults to "https://www.google.com".
    // net.SplitHostPort("https://www.google.com") fails.
    // We need to strip scheme.

    // Let's assume the user passes host:port or we fix the parsing.
    // The audit patch snippet:
    // parsed := *targetUrl
    // host, port, err := net.SplitHostPort(parsed)
    // ...

    // I will implement a slightly robust version that handles the default value too.

    target := *targetUrl
    // Strip scheme
    if len(target) > 8 && target[:8] == "https://" {
        target = target[8:]
    } else if len(target) > 7 && target[:7] == "http://" {
        target = target[7:]
    }
    // Remove path
    for i := 0; i < len(target); i++ {
        if target[i] == '/' {
            target = target[:i]
            break
        }
    }

    host, port, err = net.SplitHostPort(target)
    if err != nil {
        host = target
        port = "443"
    }

	conn, err := dialer.Dial("tcp", net.JoinHostPort(host, port))
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
		ServerName: host,
        InsecureSkipVerify: true,
	}, helloID)

	err = uConn.Handshake()
	if err != nil {
		fmt.Printf("Handshake failed: %v\n", err)
		os.Exit(1)
	}

    // Send HTTP GET
    req := fmt.Sprintf("GET / HTTP/1.1\r\nHost: %s\r\n\r\n", host)
	_, err = uConn.Write([]byte(req))
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
