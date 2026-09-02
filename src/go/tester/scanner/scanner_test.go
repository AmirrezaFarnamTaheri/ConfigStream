// SPDX-License-Identifier: AGPL-3.0-or-later
package scanner

import (
	"net"
	"testing"
	"time"
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

func TestDeliverResultWithTimer_Success(t *testing.T) {
	ch := make(chan ScanResult, 1)
	res := ScanResult{IP: "1.1.1.1", Port: 2408, Latency: 42}
	deliverResultWithTimer(ch, res, 50*time.Millisecond)

	select {
	case got := <-ch:
		if got != res {
			t.Fatalf("got %+v, want %+v", got, res)
		}
	default:
		t.Fatal("expected result in channel")
	}
}

func TestDeliverResultWithTimer_Timeout(t *testing.T) {
	ch := make(chan ScanResult) // unbuffered, no receiver
	res := ScanResult{IP: "1.1.1.1", Port: 2408, Latency: 42}
	start := time.Now()
	deliverResultWithTimer(ch, res, 10*time.Millisecond)
	elapsed := time.Since(start)
	if elapsed < 10*time.Millisecond {
		t.Fatalf("expected timeout to take at least 10ms, took %v", elapsed)
	}
}

func BenchmarkConstructHandshakePacket(b *testing.B) {
	for i := 0; i < b.N; i++ {
		if packet := ConstructHandshakePacket(); len(packet) != HandshakeLen {
			b.Fatal("invalid packet")
		}
	}
}

func BenchmarkDeliverResultTimer(b *testing.B) {
	resultsChan := make(chan ScanResult, 1)
	res := ScanResult{IP: "1.1.1.1", Port: 2408, Latency: 10}

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		deliverResultWithTimer(resultsChan, res, 50*time.Millisecond)
		<-resultsChan
	}
}
