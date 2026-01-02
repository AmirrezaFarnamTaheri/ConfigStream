// SPDX-License-Identifier: AGPL-3.0-or-later
package scanner

import (
	"crypto/rand"
	"fmt"
	mrand "math/rand"
	"net"
	"sync"
	"time"

	"golang.org/x/crypto/curve25519"
)

// Standard Cloudflare WARP CIDR ranges
var DefaultCidrs = []string{
	"162.159.192.0/24", "162.159.193.0/24", "162.159.195.0/24",
	"188.114.96.0/24", "188.114.97.0/24", "188.114.98.0/24", "188.114.99.0/24",
}

// WireGuard Handshake Initiation Packet Constants
const (
	HandshakeType    = 1 // initiation
	HandshakeLen     = 148
	ReservedLen      = 3
	SenderIndexLen   = 4
	UnencryptedEphLen= 32
	EncryptedStatic  = 48 // 32 key + 16 auth tag
	EncryptedTime    = 28 // 12 time + 16 auth tag
	MacLen           = 16
)

type ScanResult struct {
	IP      string `json:"ip"`
	Port    int    `json:"port"`
	Latency int64  `json:"latency"` // milliseconds
}

// ConstructHandshakePacket creates a valid-looking WireGuard initiation packet.
// Note: For pure scanning (latency check), we don't necessarily need a *valid* cryptographic
// handshake that creates a session. We just need the server to parse it and reply (even with a rejection).
// Cloudflare servers usually reply to formatted handshake packets.
func ConstructHandshakePacket() []byte {
	packet := make([]byte, HandshakeLen)

	// 1. Type (1 byte)
	packet[0] = HandshakeType

	// 2. Reserved (3 bytes) - Zeroed by make()

	// 3. Sender Index (4 bytes) - Random arbitrary ID
	rand.Read(packet[4:8])

	// 4. Ephemeral Public Key (32 bytes)
	// We generate a random private key and derive the public key
	var priv [32]byte
	var pub [32]byte
	rand.Read(priv[:])
	curve25519.ScalarBaseMult(&pub, &priv)
	copy(packet[8:40], pub[:])

	// 5. Encrypted Static & Timestamp (48 + 28 bytes)
	// For a strict scanner, we would encrypt our static public key here.
	// However, for scanning "aliveness", filling this with random noise
	// often triggers a "cookie reply" or "under load" response from the server,
	// which is sufficient to measure RTT.
	rand.Read(packet[40 : 40+EncryptedStatic+EncryptedTime])

	// 6. MAC1 & MAC2 (16 + 16 bytes)
	// Again, strictly these are Blake2s hashes. Random noise works for simple liveness
	// because the server validates the packet structure first.
	// If strict validation fails, we can implement full Blake2s hashing.
	// For now, leave zeroed or random.

	return packet
}

// RunScan executes the concurrent scan using a single UDP socket for better efficiency.
// This reduces file descriptor usage and system call overhead compared to opening a new socket for every IP.
func RunScan(workers int, timeout time.Duration, limit int, cidrs []string, resultsChan chan<- ScanResult) {
	// 1. Generate IPs
	targetIPs := generateIPList(cidrs)
	if limit > 0 && len(targetIPs) > limit {
		targetIPs = targetIPs[:limit]
	}

	// 2. Setup UDP Listener
	// Listen on an ephemeral port
	conn, err := net.ListenPacket("udp4", ":0")
	if err != nil {
		fmt.Printf("Error creating scanner socket: %v\n", err)
		return
	}
	defer conn.Close()

	// 3. Pre-calculate packet
	basePacket := ConstructHandshakePacket()

	// 4. Map to track pending requests: IP:Port string -> StartTime
	// Note: In high concurrency, a map with mutex might be a bottleneck.
	// For a simple scanner, we can rely on "send and forget" and just process any valid response.
	// But we need to calculate latency, so we need the start time.
	// Alternative: Encode timestamp into the Reserved/SenderIndex part of the packet.
	// WireGuard Reserved is 3 bytes, Sender Index is 4 bytes. We can use SenderIndex.

	// Implementation Strategy:
	// - Sender Goroutine: Pumps packets to target IPs.
	// - Receiver Goroutine: Reads responses, calculates latency.

	// Using a concurrent map for tracking timestamps.
	pending := sync.Map{}

	// Channel to signal completion
	done := make(chan struct{})

	// Receiver Routine
	go func() {
		defer close(done)
		buf := make([]byte, 1024)
		for {
			// Respect caller timeout budget when waiting for stragglers
			conn.SetReadDeadline(time.Now().Add(timeout))
			n, addr, err := conn.ReadFrom(buf)
			if err != nil {
				if ne, ok := err.(net.Error); ok && ne.Timeout() {
					return
				}
				continue
			}

			recvTime := time.Now()

			// Validate minimal length
			if n < 32 {
				continue
			}

			// Validate Response Type (2=Response, 4=Cookie Reply)
			msgType := buf[0]
			if msgType != 2 && msgType != 3 && msgType != 4 {
				continue
			}

			// Extract IP from address
			ipStr, _, _ := net.SplitHostPort(addr.String())

			// Retrieve start time
			if val, ok := pending.LoadAndDelete(ipStr); ok {
				startTime := val.(time.Time)
				latency := recvTime.Sub(startTime).Milliseconds()

				resultsChan <- ScanResult{
					IP:      ipStr,
					Port:    2408, // Assuming standard port
					Latency: latency,
				}
			}
		}
	}()

	// Sender Goroutines
	var wg sync.WaitGroup
	ipChan := make(chan string, len(targetIPs))
	for _, ip := range targetIPs {
		ipChan <- ip
	}
	close(ipChan)

	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for ip := range ipChan {
				addr, err := net.ResolveUDPAddr("udp4", fmt.Sprintf("%s:2408", ip))
				if err != nil {
					continue
				}

				// Store start time
				pending.Store(ip, time.Now())

				// Send
				_, err = conn.WriteTo(basePacket, addr)
				if err != nil {
					pending.Delete(ip)
				}
			}
		}()
	}

	wg.Wait() // Wait for all senders to finish

	// After sending, wait for receiver to drain up to timeout budget
	select {
	case <-done:
	case <-time.After(timeout):
	}
}

// checkEndpoint is deprecated in favor of batch scanning but kept for compatibility.
// It creates a new socket per call (inefficient).
func checkEndpoint(ip string, port int, timeout time.Duration, packet []byte) (int64, error) {
	addr := fmt.Sprintf("%s:%d", ip, port)

	// Create UDP Connection
	conn, err := net.DialTimeout("udp", addr, timeout)
	if err != nil {
		return 0, err
	}
	defer conn.Close()

	// Write Packet
	start := time.Now()
	if _, err := conn.Write(packet); err != nil {
		return 0, err
	}

	// Set Deadline for Read
	conn.SetReadDeadline(time.Now().Add(timeout))

	// Wait for Reply
	buf := make([]byte, 1024)
	n, err := conn.Read(buf)
	if err != nil {
		return 0, err
	}

	latency := time.Since(start).Milliseconds()

	if n >= 32 {
		msgType := buf[0]
		if msgType == 2 || msgType == 3 || msgType == 4 {
			return latency, nil
		}
	}

	return 0, fmt.Errorf("invalid response type")
}

func generateIPList(cidrs []string) []string {
	var ips []string
	for _, cidr := range cidrs {
		ip, ipnet, err := net.ParseCIDR(cidr)
		if err != nil {
			continue
		}
		for ip := ip.Mask(ipnet.Mask); ipnet.Contains(ip); inc(ip) {
			// Skip network and broadcast (simplified)
			ips = append(ips, ip.String())
		}
	}
	// Shuffle IPs here for better distribution
	mrand.Seed(time.Now().UnixNano())
	mrand.Shuffle(len(ips), func(i, j int) {
		ips[i], ips[j] = ips[j], ips[i]
	})
	return ips
}

func inc(ip net.IP) {
	for j := len(ip) - 1; j >= 0; j-- {
		ip[j]++
		if ip[j] > 0 {
			break
		}
	}
}
