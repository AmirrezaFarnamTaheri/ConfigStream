package main

import (
	"bufio"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"net"
	"os"
	"sync"
	"time"
)

// ProxyInput represents the incoming JSON object
type ProxyInput struct {
	ID        string `json:"id"`
	Protocol  string `json:"protocol"`
	Address   string `json:"address"`
	Port      int    `json:"port"`
	Details   map[string]interface{} `json:"details"`
}

// ProxyResult represents the result to be written to stdout
type ProxyResult struct {
	ID        string  `json:"id"`
	Alive     bool    `json:"alive"`
	Latency   float64 `json:"latency"` // ms
	Error     string  `json:"error,omitempty"`
	Honeypot  bool    `json:"honeypot"`
}

var (
	workerCount int
	timeout     time.Duration
	secretKey   string
)

func main() {
	flag.IntVar(&workerCount, "workers", 50, "Number of concurrent workers")
	flag.DurationVar(&timeout, "timeout", 5*time.Second, "Timeout per test")
	flag.StringVar(&secretKey, "secret", "", "Honeypot signing secret")
	flag.Parse()

	// Input/Output channels
	jobs := make(chan ProxyInput, workerCount*2)
	results := make(chan ProxyResult, workerCount*2)

	// Start workers
	var wg sync.WaitGroup
	for i := 0; i < workerCount; i++ {
		wg.Add(1)
		go worker(jobs, results, &wg)
	}

	// Start result writer
	go func() {
		encoder := json.NewEncoder(os.Stdout)
		for res := range results {
			encoder.Encode(res)
		}
	}()

	// Read stdin
	scanner := bufio.NewScanner(os.Stdin)
	for scanner.Scan() {
		var p ProxyInput
		if err := json.Unmarshal(scanner.Bytes(), &p); err == nil {
			jobs <- p
		}
	}
	close(jobs)

	wg.Wait()
	close(results)
}

func worker(jobs <-chan ProxyInput, results chan<- ProxyResult, wg *sync.WaitGroup) {
	defer wg.Done()

	for p := range jobs {
		start := time.Now()
		alive := false
		var lat float64
		var errStr string
		honeypot := false

		// 1. Basic TCP Connect
		address := fmt.Sprintf("%s:%d", p.Address, p.Port)
		conn, err := net.DialTimeout("tcp", address, timeout)

		if err != nil {
			alive = false
			errStr = err.Error()
		} else {
			alive = true
			lat = float64(time.Since(start).Milliseconds())
			conn.Close()

			// 2. Honeypot Verification
			// In Phase 4, we want to verify if the proxy is a MITM by checking a signature.
			// However, to check the signature we must CONNECT THROUGH the proxy to the Canary Worker.
			// As established, doing full protocol handshake (VMess etc) here is complex without full Singbox lib.
			//
			// BUT, if we have the secret key, we can verify signatures locally if we were passed a signed token.
			// OR we can assume this Go tester is the "Canary Client".

			// For the "Zero Budget" simplified implementation:
			// If the user provided a Secret Key, we treat this check as "Check if IP is in Honeypot List"
			// or perform a passive check.

			// Real Honeypot Signature verification requires:
			// Client -> Proxy -> Worker(Token) -> SignedResponse
			// Client verifies SignedResponse matches HMAC(Token, Secret).

			// Since we can't easily route through VMess in this lightweight Go binary yet,
			// we will skip the active Canary check here and rely on the Python fallback for "Strict Security" mode.
			// However, we CAN implement the HMAC verification logic if needed.

			// Placeholder logic: if the IP matches a known bad pattern or we implement the
			// HTTP check for HTTP/SOCKS proxies easily.

			if secretKey != "" {
				// Logic to verify signature would go here if we fetched a URL
				pass := true // Assume pass for now since we didn't fetch
				if !pass {
					honeypot = true
				}
			}
		}

		results <- ProxyResult{
			ID:       p.ID,
			Alive:    alive,
			Latency:  lat,
			Error:    errStr,
			Honeypot: honeypot,
		}
	}
}

func verifyHoneypot(token, signature, secret string) bool {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(token))
	expected := hex.EncodeToString(mac.Sum(nil))
	return hmac.Equal([]byte(signature), []byte(expected))
}
