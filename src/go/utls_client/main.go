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

func parseTarget(raw string) (*url.URL, string, string, error) {
	parsed, err := url.Parse(raw)
	if err != nil || parsed.Host == "" {
		return nil, "", "", fmt.Errorf("invalid URL")
	}
	if parsed.Scheme != "https" {
		return nil, "", "", fmt.Errorf("unsupported URL scheme %q", parsed.Scheme)
	}
	if parsed.User != nil {
		return nil, "", "", fmt.Errorf("URL credentials are not supported")
	}
	host := parsed.Hostname()
	if host == "" {
		return nil, "", "", fmt.Errorf("missing target host")
	}
	port := parsed.Port()
	if port == "" {
		port = "443"
	}
	return parsed, host, port, nil
}

func buildHTTPRequest(parsed *url.URL) string {
	return fmt.Sprintf("GET %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\nConnection: close\r\n\r\n",
		parsed.RequestURI(), parsed.Host)
}

// uTLS client for verifying connectivity and TLS fingerprint randomization.
// Performs a TLS handshake with the specified fingerprint and sends a basic
// HTTP GET to confirm the connection is functional.

func main() {
	targetURL := flag.String("url", "https://www.google.com", "Target URL to fetch")
	fingerprint := flag.String("fp", "chrome", "Fingerprint ID (chrome, firefox, ios, random)")
	flag.Parse()

	if *targetURL == "" {
		fmt.Println("Error: URL is required")
		os.Exit(1)
	}

	dialer := &net.Dialer{
		Timeout: 10 * time.Second,
	}

	parsed, host, port, err := parseTarget(*targetURL)
	if err != nil {
		fmt.Printf("Invalid URL: %s (%v)\n", *targetURL, err)
		os.Exit(1)
	}

	conn, err := dialer.Dial("tcp", net.JoinHostPort(host, port))
	if err != nil {
		fmt.Printf("Failed to dial: %v\n", err)
		os.Exit(1)
	}
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
		ServerName: host,
	}, helloID)

	err = uConn.Handshake()
	if err != nil {
		fmt.Printf("Handshake failed: %v\n", err)
		os.Exit(1)
	}
	defer uConn.Close()

	// Include User-Agent header to avoid trivial automated-traffic detection.
	// For a fingerprint-evasion tool, sending no UA undermines the purpose.
	req := buildHTTPRequest(parsed)
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
