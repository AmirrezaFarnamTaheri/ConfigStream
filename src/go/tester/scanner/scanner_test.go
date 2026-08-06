// SPDX-License-Identifier: AGPL-3.0-or-later
package scanner

import (
	"net"
	"testing"
)

func TestConstructHandshakePacketShape(t *testing.T) {
	packet := ConstructHandshakePacket()
	if len(packet) != HandshakeLen {
		t.Fatalf("len(packet) = %d, want %d", len(packet), HandshakeLen)
	}
	if packet[0] != HandshakeType {
		t.Fatalf("packet type = %d, want %d", packet[0], HandshakeType)
	}
	if packet[1] != 0 || packet[2] != 0 || packet[3] != 0 {
		t.Fatal("reserved bytes must be zero")
	}
}

func TestGenerateIPListSkipsIPv4NetworkAndBroadcast(t *testing.T) {
	ips := generateIPList([]string{"192.0.2.0/24"})
	if len(ips) != 254 {
		t.Fatalf("len(ips) = %d, want 254", len(ips))
	}
	for _, ip := range ips {
		if ip == "192.0.2.0" || ip == "192.0.2.255" {
			t.Fatalf("reserved address included: %s", ip)
		}
	}
}

func TestInc(t *testing.T) {
	ip := net.IPv4(192, 0, 2, 254).To4()
	inc(ip)
	if got := ip.String(); got != "192.0.2.255" {
		t.Fatalf("inc() = %s", got)
	}
}

func BenchmarkConstructHandshakePacket(b *testing.B) {
	for i := 0; i < b.N; i++ {
		if packet := ConstructHandshakePacket(); len(packet) != HandshakeLen {
			b.Fatal("invalid packet")
		}
	}
}
