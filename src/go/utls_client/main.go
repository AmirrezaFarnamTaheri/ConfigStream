// SPDX-License-Identifier: AGPL-3.0-or-later
package main

import (
	"flag"
	"fmt"
	"io"
	"net"
	"net/url"
	"os"
	"time"

	tls "github.com/refraction-networking/utls"
)

// uTLS client for verifying connectivity and TLS fingerprint randomization.
// Performs a TLS handshake with the specified fingerprint and sends a basic
// HTTP GET to confirm the connection is functional.

func main() {
	targetURL := flag.String("url", "https://www.google.com", "Target URL to fetch")
	_ = flag.String("proxy", "", "Proxy address (host:port) - reserved for future use")
	fingerprint := flag.String("fp", "chrome", "Fingerprint ID (chrome, firefox, ios, random)")
	// InsecureSkipVerify is now a CLI flag defaulting to false.
	// Previously hardcoded to true, which disabled TLS cert validation entirely,
	// allowing MITM attacks -- especially dangerous for anti-censorship use.
	skipVerify := flag.Bool("skip-verify", false, "Skip TLS certificate verification (UNSAFE)")
	flag.Parse()

	if *targetURL == "" {
		fmt.Println("Error: URL is required")
		os.Exit(1)
	}

	dialer := &net.Dialer{
		Timeout: 10 * time.Second,
	}

	// Use net/url.Parse for robust URL parsing instead of fragile manual
	// byte-offset stripping. The old approach failed for URLs with auth, query
	// params, or non-standard ports.
	parsed, err := url.Parse(*targetURL)
	if err != nil || parsed.Host == "" {
		fmt.Printf("Invalid URL: %s\n", *targetURL)
		os.Exit(1)
	}

	host := parsed.Hostname()
	port := parsed.Port()
	if port == "" {
		switch parsed.Scheme {
		case "https":
			port = "443"
		case "http":
			port = "80"
		default:
			port = "443"
		}
	}

	conn, err := dialer.Dial("tcp", net.JoinHostPort(host, port))
	if err != nil {
		fmt.Printf("Failed to dial: %v\n", err)
		os.Exit(1)
	}
	// Add defer conn.Close() to prevent connection leaks.
	// Previously missing, causing TCP connections to linger in TIME_WAIT.
	defer conn.Close()

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
		ServerName:         host,
		InsecureSkipVerify: *skipVerify,
	}, helloID)

	err = uConn.Handshake()
	if err != nil {
		fmt.Printf("Handshake failed: %v\n", err)
		os.Exit(1)
	}
	defer uConn.Close()

	// Include User-Agent header to avoid trivial automated-traffic detection.
	// For a fingerprint-evasion tool, sending no UA undermines the purpose.
	req := fmt.Sprintf("GET %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\nConnection: close\r\n\r\n",
		parsed.RequestURI(), host)
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
