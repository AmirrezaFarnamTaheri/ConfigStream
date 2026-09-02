// SPDX-License-Identifier: AGPL-3.0-or-later
package scanner

import (
	"crypto/rand"
	"fmt"
	"log"
	mrand "math/rand"
	"net"
	"strconv"
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
	HandshakeType     = 1 // initiation
	HandshakeLen      = 148
	ReservedLen       = 3
	SenderIndexLen    = 4
	UnencryptedEphLen = 32
	EncryptedStatic   = 48 // 32 key + 16 auth tag
	EncryptedTime     = 28 // 12 time + 16 auth tag
	MacLen            = 16
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
	// Check crypto/rand.Read errors to prevent sending zeroed packets
	if _, err := rand.Read(packet[4:8]); err != nil {
		return nil
	}

	// 4. Ephemeral Public Key (32 bytes)
	// We generate a random private key and derive the public key
	var priv [32]byte
	var pub [32]byte
	if _, err := rand.Read(priv[:]); err != nil {
		return nil
	}
	curve25519.ScalarBaseMult(&pub, &priv)
	copy(packet[8:40], pub[:])

	// 5. Encrypted Static & Timestamp (48 + 28 bytes)
	// For a strict scanner, we would encrypt our static public key here.
	// However, for scanning "aliveness", filling this with random noise
	// often triggers a "cookie reply" or "under load" response from the server,
	// which is sufficient to measure RTT.
	if _, err := rand.Read(packet[40 : 40+EncryptedStatic+EncryptedTime]); err != nil {
		return nil
	}

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
		// Use log.Printf instead of fmt.Printf to write to stderr.
		// fmt.Printf writes to stdout which corrupts the NDJSON result stream
		// that the Python consumer is parsing, causing decode errors.
		log.Printf("Error creating scanner socket: %v", err)
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
	// Key: IP:Port string (e.g. "1.1.1.1:2408") -> StartTime
	pending := sync.Map{}

	// Channel to signal completion
	done := make(chan struct{})

	// WaitGroup to track senders
	var wg sync.WaitGroup

	// Signal when sending is complete
	sendDone := make(chan struct{})

	// Receiver Routine
	go func() {
		defer close(done)
		buf := make([]byte, 1024)
		// The receiver is the sole result sender, so it owns one reusable
		// delivery timer for the whole scan rather than allocating a timer for
		// each received packet.
		deliveryTimer := time.NewTimer(time.Hour)
		if !deliveryTimer.Stop() {
			<-deliveryTimer.C
		}
		defer deliveryTimer.Stop()

		// No deadline while sending; once sending completes, start the grace-period timer.
		var end time.Time
		sending := true

		for {
			if sending {
				select {
				case <-sendDone:
					sending = false
					end = time.Now().Add(timeout)
				default:
					// Avoid blocking indefinitely; poll until sending finishes.
					// We set a short deadline to allow checking sendDone periodically.
					conn.SetReadDeadline(time.Now().Add(200 * time.Millisecond))
				}
			} else {
				conn.SetReadDeadline(end)
			}

			n, addr, err := conn.ReadFrom(buf)
			if err != nil {
				if ne, ok := err.(net.Error); ok && ne.Timeout() {
					// If we are still sending, a timeout is just a poll tick
					if !sending {
						// Sending done + timeout reached = we are finished
						return
					}
					continue
				}
				// Removed ne.Temporary() check (always returns false
				// in Go 1.18+, causing premature exit on any non-timeout error).
				// During the sending phase, non-timeout errors are recoverable.
				// After sending completes, any error means we're done.
				if !sending {
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

			// Extract IP and Port from address
			// Use composite key (IP:Port) to support multi-port scanning
			// Previously used just IP, which caused collisions if scanning multiple ports on same IP.
			// addr.String() returns "IP:Port" already.
			endpointStr := addr.String()
			ipStr, portStr, _ := net.SplitHostPort(endpointStr)

			// Try to find by full endpoint key
			if val, ok := pending.LoadAndDelete(endpointStr); ok {
				startTime := val.(time.Time)
				latency := recvTime.Sub(startTime).Milliseconds()

				port := 2408
				if p, err := strconv.Atoi(portStr); err == nil {
					port = p
				}

				// Avoid deadlock if results consumer is slow/unbuffered, but don't silently lose all results.
				deliverResultWithTimer(resultsChan, ScanResult{
					IP:      ipStr,
					Port:    port,
					Latency: latency,
				}, deliveryTimer, 50*time.Millisecond)
			} else {
				// Fallback if key was just IP (unlikely given sender logic below, but safe)
				if val, ok := pending.LoadAndDelete(ipStr); ok {
					startTime := val.(time.Time)
					latency := recvTime.Sub(startTime).Milliseconds()

					deliverResultWithTimer(resultsChan, ScanResult{
						IP:      ipStr,
						Port:    2408,
						Latency: latency,
					}, deliveryTimer, 50*time.Millisecond)
				}
			}
		}
	}()

	// Sender Goroutines
	ipChan := make(chan string, len(targetIPs))
	for _, ip := range targetIPs {
		ipChan <- ip
	}
	close(ipChan)

	// Rate Limit Throttling
	// Calculate delay per packet to avoid bursting network stack (e.g. 1000 pps limit)
	// If workers=50, each worker sends 1 packet then waits a bit.
	// Simple sleep strategy: 1ms sleep every N packets or just 1ms per packet if paranoid.
	// Given 'workers' concurrency, raw speed is high.
	// Let's add a small ticker to the shared consumption if possible, or just sleep in worker.

	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for ip := range ipChan {
				// Support dynamic port if needed, defaulting to 2408 for now as per CIDR logic
				targetPort := 2408
				endpoint := fmt.Sprintf("%s:%d", ip, targetPort)

				addr, err := net.ResolveUDPAddr("udp4", endpoint)
				if err != nil {
					continue
				}

				// Store start time with composite key
				pending.Store(endpoint, time.Now())

				// Send
				_, err = conn.WriteTo(basePacket, addr)
				if err != nil {
					pending.Delete(endpoint)
				}

				// Throttle sends slightly to prevent packet loss at OS buffer
				time.Sleep(1 * time.Millisecond)
			}
		}()
	}

	// Monitor senders completion
	go func() {
		wg.Wait()
		close(sendDone)
	}()

	// Wait for receiver to finish (which implies sending finished + timeout expired)
	<-done
}

func generateIPList(cidrs []string) []string {
	var ips []string
	for _, cidr := range cidrs {
		ip, ipnet, err := net.ParseCIDR(cidr)
		if err != nil {
			continue
		}
		for ip := ip.Mask(ipnet.Mask); ipnet.Contains(ip); inc(ip) {
			// Actually skip network (.0) and broadcast (.255) addresses.
			// Previously the comment said "skip" but the code didn't filter them,
			// wasting time scanning unreachable addresses and triggering alerts.
			last := ip[len(ip)-1]
			if last == 0 || last == 255 {
				continue
			}
			ips = append(ips, ip.String())
		}
	}
	// Shuffle IPs for better distribution
	// Removed mrand.Seed() call (auto-seeded since Go 1.20)
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

// deliverResultWithTimer uses a caller-owned timer to bound delivery without
// allocating a fresh timer for every packet.
func deliverResultWithTimer(resultsChan chan<- ScanResult, res ScanResult, timer *time.Timer, timeout time.Duration) {
	if !timer.Stop() {
		select {
		case <-timer.C:
		default:
		}
	}
	timer.Reset(timeout)

	select {
	case resultsChan <- res:
		if !timer.Stop() {
			select {
			case <-timer.C:
			default:
			}
		}
	case <-timer.C:
	}
}
