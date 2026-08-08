// SPDX-License-Identifier: AGPL-3.0-or-later
package main

import (
	"strings"
	"testing"
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
