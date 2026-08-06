// SPDX-License-Identifier: AGPL-3.0-or-later
package main

import "testing"

func TestParseConfigRejectsEmpty(t *testing.T) {
	if _, _, err := parseConfig("  "); err == nil {
		t.Fatal("expected empty config to fail")
	}
}

func TestParseConfigSingleOutbound(t *testing.T) {
	outs, tag, err := parseConfig(`{"type":"direct","tag":"ignored"}`)
	if err != nil {
		t.Fatalf("parseConfig() error = %v", err)
	}
	if tag != "proxy" {
		t.Fatalf("tag = %q, want proxy", tag)
	}
	if len(outs) != 1 {
		t.Fatalf("len(outbounds) = %d, want 1", len(outs))
	}
	if outs[0].Tag != "proxy" {
		t.Fatalf("outbound tag = %q, want proxy", outs[0].Tag)
	}
}

func TestParseConfigPreservesOutboundArray(t *testing.T) {
	config := `[{"type":"direct","tag":"direct"},{"type":"socks","tag":"proxy","server":"127.0.0.1","server_port":1080}]`
	outs, tag, err := parseConfig(config)
	if err != nil {
		t.Fatalf("parseConfig() error = %v", err)
	}
	if tag != "proxy" {
		t.Fatalf("tag = %q, want proxy", tag)
	}
	if len(outs) != 2 {
		t.Fatalf("len(outbounds) = %d, want 2", len(outs))
	}
	if outs[1].Tag != "proxy" {
		t.Fatalf("entry outbound tag = %q, want proxy", outs[1].Tag)
	}
}

func FuzzParseConfig(f *testing.F) {
	for _, seed := range []string{"", `{}`, `{"type":"direct"}`, `[{"type":"direct","tag":"proxy"}]`, `{"outbounds":[]}`} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, raw string) {
		_, _, _ = parseConfig(raw)
	})
}

func BenchmarkParseConfig(b *testing.B) {
	const config = `[{"type":"direct","tag":"direct"},{"type":"socks","tag":"proxy","server":"127.0.0.1","server_port":1080}]`
	for i := 0; i < b.N; i++ {
		if _, _, err := parseConfig(config); err != nil {
			b.Fatal(err)
		}
	}
}
