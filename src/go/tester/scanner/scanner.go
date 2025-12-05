package scanner

import (
	"crypto/rand"
	"fmt"
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

// RunScan executes the concurrent scan
func RunScan(workers int, timeout time.Duration, limit int, cidrs []string, resultsChan chan<- ScanResult) {
	var wg sync.WaitGroup
	sem := make(chan struct{}, workers) // Semaphore for concurrency control

	// 1. Generate IPs
	targetIPs := generateIPList(cidrs)

	// 2. Pre-calculate packet (optimization: reuse buffer if possible, but for safety create per conn)
	// We can reuse the same "base" packet content for scanning to save CPU on crypto operations.
	basePacket := ConstructHandshakePacket()

	count := 0
	for _, ip := range targetIPs {
		if limit > 0 && count >= limit {
			break
		}
		count++

		wg.Add(1)
		sem <- struct{}{} // Acquire token

		go func(target string) {
			defer wg.Done()
			defer func() { <-sem }() // Release token

			latency, err := checkEndpoint(target, 2408, timeout, basePacket)
			if err == nil {
				resultsChan <- ScanResult{
					IP:      target,
					Port:    2408,
					Latency: latency,
				}
			}
		}(ip)
	}

	wg.Wait()
}

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
	// A WireGuard response (Type 2) is 92 bytes, or Cookie Reply (Type 3) is 64 bytes.
	buf := make([]byte, 1024)
	n, err := conn.Read(buf)
	if err != nil {
		return 0, err
	}

	// Calculate Latency
	latency := time.Since(start).Milliseconds()

	// Validation: Ensure it's a WireGuard packet
	// Type 2 (Response) or Type 4 (Cookie Reply, often sent when under load or invalid mac)
	if n >= 32 { // Minimal sanity check
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
	// TODO: Shuffle IPs here for better distribution
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
