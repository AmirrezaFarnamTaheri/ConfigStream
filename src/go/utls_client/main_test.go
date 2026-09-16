// SPDX-License-Identifier: AGPL-3.0-or-later
package main

import (
	"bufio"
	"fmt"
	"io"
	"net"
	"strings"
	"testing"
	"time"
)

func TestParseTarget(t *testing.T) {
	tests := []struct {
		name     string
		raw      string
		wantHost string
		wantPort string
		wantURI  string
		wantErr  bool
	}{
		{name: "https default", raw: "https://example.com/path?q=1", wantHost: "example.com", wantPort: "443", wantURI: "/path?q=1"},
		{name: "http rejected", raw: "http://example.com", wantErr: true},
		{name: "custom port", raw: "https://example.com:8443/a", wantHost: "example.com", wantPort: "8443", wantURI: "/a"},
		{name: "ipv6", raw: "https://[2001:db8::1]:9443/", wantHost: "2001:db8::1", wantPort: "9443", wantURI: "/"},
		{name: "credentials rejected", raw: "https://user:secret@example.com/", wantErr: true},
		{name: "missing host", raw: "https:///path", wantErr: true},
		{name: "unsupported scheme", raw: "ftp://example.com/file", wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			parsed, host, port, err := parseTarget(tt.raw)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error")
				}
				return
			}
			if err != nil {
				t.Fatalf("parseTarget() error = %v", err)
			}
			if host != tt.wantHost {
				t.Fatalf("host = %q, want %q", host, tt.wantHost)
			}
			if port != tt.wantPort {
				t.Fatalf("port = %q, want %q", port, tt.wantPort)
			}
			if got := parsed.RequestURI(); got != tt.wantURI {
				t.Fatalf("RequestURI = %q, want %q", got, tt.wantURI)
			}
		})
	}
}

func TestBuildHTTPRequestPreservesNonDefaultPort(t *testing.T) {
	parsed, _, _, err := parseTarget("https://example.com:8443/path?q=1")
	if err != nil {
		t.Fatal(err)
	}
	request := buildHTTPRequest(parsed)
	if want := "Host: example.com:8443\r\n"; !strings.Contains(request, want) {
		t.Fatalf("request does not contain %q: %q", want, request)
	}
}

func TestParseProxyBareAddressDefaultsToHTTP(t *testing.T) {
	proxyURL, err := parseProxy("127.0.0.1:8080")
	if err != nil {
		t.Fatalf("parseProxy returned error: %v", err)
	}
	if proxyURL == nil {
		t.Fatal("parseProxy returned nil URL")
	}
	if proxyURL.Scheme != "http" || proxyURL.Hostname() != "127.0.0.1" || proxyURL.Port() != "8080" {
		t.Fatalf("unexpected parsed proxy: %#v", proxyURL)
	}
}

func TestParseProxyRejectsUnsupportedOrCredentialedURLs(t *testing.T) {
	for _, raw := range []string{
		"socks5://127.0.0.1:1080",
		"http://user:pass@127.0.0.1:8080",
		"http://127.0.0.1:8080/path",
		"http://127.0.0.1:8080?mode=unsafe",
	} {
		if _, err := parseProxy(raw); err == nil {
			t.Fatalf("parseProxy(%q) unexpectedly succeeded", raw)
		}
	}
}

func TestHelloIDRejectsUnknownFingerprint(t *testing.T) {
	if _, ok := helloIDForFingerprint("not-a-browser"); ok {
		t.Fatal("unknown fingerprint was silently accepted")
	}
}

func TestDialTargetUsesHTTPConnectAndPreservesBufferedBytes(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	defer listener.Close()

	proxyErr := make(chan error, 1)
	go func() {
		conn, acceptErr := listener.Accept()
		if acceptErr != nil {
			proxyErr <- acceptErr
			return
		}
		defer conn.Close()

		reader := bufio.NewReader(conn)
		requestLine, readErr := reader.ReadString('\n')
		if readErr != nil {
			proxyErr <- readErr
			return
		}
		if requestLine != "CONNECT example.com:443 HTTP/1.1\r\n" {
			proxyErr <- fmt.Errorf("unexpected CONNECT line %q", requestLine)
			return
		}
		for {
			line, lineErr := reader.ReadString('\n')
			if lineErr != nil {
				proxyErr <- lineErr
				return
			}
			if line == "\r\n" {
				break
			}
		}
		if _, writeErr := io.WriteString(
			conn,
			"HTTP/1.1 200 Connection Established\r\n\r\nhello",
		); writeErr != nil {
			proxyErr <- writeErr
			return
		}
		proxyErr <- nil
	}()

	dialer := &net.Dialer{Timeout: time.Second}
	conn, err := dialTarget(dialer, "example.com:443", listener.Addr().String())
	if err != nil {
		t.Fatalf("dialTarget: %v", err)
	}
	defer conn.Close()

	payload := make([]byte, len("hello"))
	if _, err := io.ReadFull(conn, payload); err != nil {
		t.Fatalf("read tunneled payload: %v", err)
	}
	if string(payload) != "hello" {
		t.Fatalf("unexpected tunneled payload %q", payload)
	}
	if err := <-proxyErr; err != nil {
		t.Fatal(err)
	}
}

func TestParseProxyEmptyMeansDirect(t *testing.T) {
	proxyURL, err := parseProxy("   ")
	if err != nil {
		t.Fatalf("parseProxy returned error: %v", err)
	}
	if proxyURL != nil {
		t.Fatalf("expected direct mode, got %v", proxyURL)
	}
}

func TestProxyErrorDoesNotEchoCredentialMaterial(t *testing.T) {
	_, err := parseProxy("http://super-secret:password@127.0.0.1:8080")
	if err == nil {
		t.Fatal("credentialed proxy unexpectedly accepted")
	}
	if strings.Contains(err.Error(), "super-secret") || strings.Contains(err.Error(), "password") {
		t.Fatalf("proxy parse error leaked credentials: %v", err)
	}
}

func FuzzParseTarget(f *testing.F) {
	for _, seed := range []string{"https://example.com", "http://127.0.0.1:8080/a", "https://[::1]/", "not a url"} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, raw string) {
		_, _, _, _ = parseTarget(raw)
	})
}

func BenchmarkParseTarget(b *testing.B) {
	for i := 0; i < b.N; i++ {
		if _, _, _, err := parseTarget("https://example.com:8443/path?q=1"); err != nil {
			b.Fatal(err)
		}
	}
}
