// SPDX-License-Identifier: AGPL-3.0-or-later
package main

import (
	"bufio"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	tls "github.com/refraction-networking/utls"
)

const proxyHandshakeTimeout = 10 * time.Second

type bufferedConn struct {
	net.Conn
	reader *bufio.Reader
}

func (conn *bufferedConn) Read(p []byte) (int, error) {
	return conn.reader.Read(p)
}

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

func parseProxy(raw string) (*url.URL, error) {
	candidate := strings.TrimSpace(raw)
	if candidate == "" {
		return nil, nil
	}
	if !strings.Contains(candidate, "://") {
		candidate = "http://" + candidate
	}
	parsed, err := url.Parse(candidate)
	if err != nil || parsed.Hostname() == "" {
		return nil, fmt.Errorf("invalid proxy URL")
	}
	if strings.ToLower(parsed.Scheme) != "http" {
		return nil, fmt.Errorf("unsupported proxy scheme %q", parsed.Scheme)
	}
	if parsed.User != nil {
		return nil, fmt.Errorf("proxy credentials are not supported in command-line arguments")
	}
	if parsed.Path != "" && parsed.Path != "/" {
		return nil, fmt.Errorf("proxy URL must not contain a path")
	}
	if parsed.RawQuery != "" || parsed.Fragment != "" {
		return nil, fmt.Errorf("proxy URL must not contain query or fragment data")
	}
	return parsed, nil
}

func dialHTTPConnect(dialer *net.Dialer, proxyURL *url.URL, target string) (net.Conn, error) {
	proxyPort := proxyURL.Port()
	if proxyPort == "" {
		proxyPort = "80"
	}
	proxyAddress := net.JoinHostPort(proxyURL.Hostname(), proxyPort)
	conn, err := dialer.Dial("tcp", proxyAddress)
	if err != nil {
		return nil, fmt.Errorf("proxy dial failed: %w", err)
	}

	failed := true
	defer func() {
		if failed {
			_ = conn.Close()
		}
	}()

	if err := conn.SetDeadline(time.Now().Add(proxyHandshakeTimeout)); err != nil {
		return nil, fmt.Errorf("proxy deadline setup failed: %w", err)
	}
	if _, err := fmt.Fprintf(
		conn,
		"CONNECT %s HTTP/1.1\r\nHost: %s\r\nProxy-Connection: Keep-Alive\r\n\r\n",
		target,
		target,
	); err != nil {
		return nil, fmt.Errorf("proxy CONNECT write failed: %w", err)
	}

	reader := bufio.NewReader(conn)
	response, err := http.ReadResponse(reader, &http.Request{Method: http.MethodConnect})
	if err != nil {
		return nil, fmt.Errorf("proxy CONNECT response failed: %w", err)
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		_ = response.Body.Close()
		return nil, fmt.Errorf("proxy CONNECT rejected with status %d", response.StatusCode)
	}
	if err := conn.SetDeadline(time.Time{}); err != nil {
		return nil, fmt.Errorf("proxy deadline reset failed: %w", err)
	}

	failed = false
	return &bufferedConn{Conn: conn, reader: reader}, nil
}

func dialTarget(dialer *net.Dialer, target string, rawProxy string) (net.Conn, error) {
	proxyURL, err := parseProxy(rawProxy)
	if err != nil {
		return nil, err
	}
	if proxyURL == nil {
		return dialer.Dial("tcp", target)
	}
	return dialHTTPConnect(dialer, proxyURL, target)
}

func buildHTTPRequest(parsed *url.URL) string {
	return fmt.Sprintf("GET %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\nConnection: close\r\n\r\n",
		parsed.RequestURI(), parsed.Host)
}

func helloIDForFingerprint(fingerprint string) (tls.ClientHelloID, bool) {
	switch strings.ToLower(strings.TrimSpace(fingerprint)) {
	case "chrome":
		return tls.HelloChrome_Auto, true
	case "firefox":
		return tls.HelloFirefox_Auto, true
	case "ios":
		return tls.HelloIOS_Auto, true
	case "random":
		return tls.HelloRandomized, true
	default:
		return tls.HelloChrome_Auto, false
	}
}

// uTLS client for verifying connectivity and TLS fingerprint randomization.
// Performs a TLS handshake with the specified fingerprint and sends a bounded
// HTTP GET probe either directly or through an explicit HTTP CONNECT proxy.
func main() {
	targetURL := flag.String("url", "https://www.google.com", "Target URL to fetch")
	fingerprint := flag.String("fp", "chrome", "Fingerprint ID (chrome, firefox, ios, random)")
	proxyAddress := flag.String("proxy", "", "Optional HTTP CONNECT proxy URL or host:port")
	flag.Parse()

	if *targetURL == "" {
		fmt.Println("Error: URL is required")
		os.Exit(1)
	}

	parsed, host, port, err := parseTarget(*targetURL)
	if err != nil {
		fmt.Printf("Invalid URL: %v\n", err)
		os.Exit(1)
	}
	helloID, supported := helloIDForFingerprint(*fingerprint)
	if !supported {
		fmt.Printf("Invalid fingerprint: unsupported fingerprint %q\n", *fingerprint)
		os.Exit(1)
	}

	dialer := &net.Dialer{Timeout: 10 * time.Second}
	target := net.JoinHostPort(host, port)
	conn, err := dialTarget(dialer, target, *proxyAddress)
	if err != nil {
		fmt.Printf("Failed to dial target: %v\n", err)
		os.Exit(1)
	}
	defer conn.Close()

	uConn := tls.UClient(conn, &tls.Config{ServerName: host}, helloID)
	if err := uConn.Handshake(); err != nil {
		fmt.Printf("Handshake failed: %v\n", err)
		os.Exit(1)
	}
	defer uConn.Close()

	req := buildHTTPRequest(parsed)
	if _, err := uConn.Write([]byte(req)); err != nil {
		fmt.Printf("Write failed: %v\n", err)
		os.Exit(1)
	}

	buf := make([]byte, 1024)
	n, err := uConn.Read(buf)
	if err != nil && err != io.EOF {
		fmt.Printf("Read failed: %v\n", err)
		os.Exit(1)
	}

	mode := "direct"
	if strings.TrimSpace(*proxyAddress) != "" {
		mode = "HTTP CONNECT proxy"
	}
	fmt.Printf("Success: %d bytes received using %s fingerprint via %s\n", n, *fingerprint, mode)
}
