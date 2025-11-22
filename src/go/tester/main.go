package main

import (
	"bufio"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"sync"
	"time"

	"github.com/sagernet/sing-box/box"
	"github.com/sagernet/sing-box/option"
)

// --- Configuration ---

const (
	MaxWorkers     = 50
	TestTimeout    = 10 * time.Second
	HoneypotSecret = "HONEYPOT_SECRET" // Env var
)

var (
	CanaryURL = os.Getenv("CANARY_URL")
)

// --- Data Structures ---

type ProxyInput struct {
	Config       string `json:"config"` // Full Sing-box outbound JSON
	ID           string `json:"id"`
	CheckHoneypot bool   `json:"check_honeypot"`
}

type TestResult struct {
	ID        string   `json:"id"`
	IsWorking bool     `json:"is_working"`
	Latency   float64  `json:"latency"`   // milliseconds
	Error     string   `json:"error,omitempty"`
	Issues    []string `json:"issues,omitempty"` // e.g. ["HONEYPOT_DETECTED"]
}

type HoneypotResponse struct {
	Signature string `json:"signature"`
}

// --- Main ---

func main() {
	workers := flag.Int("workers", MaxWorkers, "Number of concurrent workers")
	flag.Parse()

	if CanaryURL == "" {
		// Fallback or strict failure depending on policy.
		// For now, we warn but proceed.
		fmt.Fprintln(os.Stderr, "Warning: CANARY_URL not set, skipping honeypot checks")
	}

	inputChan := make(chan ProxyInput, *workers*2)
	outputChan := make(chan TestResult, *workers*2)

	var wg sync.WaitGroup

	// Start Workers
	for i := 0; i < *workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			worker(inputChan, outputChan)
		}()
	}

	// Start Output Writer
	go writer(outputChan)

	// Start Input Reader
	reader(inputChan)

	wg.Wait()
	close(outputChan)
	// Allow writer to flush
	time.Sleep(100 * time.Millisecond)
}

func reader(inputChan chan<- ProxyInput) {
	scanner := bufio.NewScanner(os.Stdin)
	for scanner.Scan() {
		line := scanner.Text()
		var p ProxyInput
		if err := json.Unmarshal([]byte(line), &p); err != nil {
			continue
		}
		inputChan <- p
	}
	close(inputChan)
}

func writer(outputChan <-chan TestResult) {
	encoder := json.NewEncoder(os.Stdout)
	for res := range outputChan {
		if err := encoder.Encode(res); err != nil {
			fmt.Fprintln(os.Stderr, "Encode error:", err)
		}
	}
}

func worker(input <-chan ProxyInput, output chan<- TestResult) {
	ctx := context.Background()

	for p := range input {
		res := TestResult{ID: p.ID}

		// 1. Basic Connectivity Test
		latency, err := testLatency(ctx, p)

		if err == nil {
			res.IsWorking = true
			res.Latency = latency

			// 2. Security / Honeypot Check (if requested and connected)
			if p.CheckHoneypot && CanaryURL != "" {
				if isHoneypot(ctx, p) {
					res.Issues = append(res.Issues, "HONEYPOT_DETECTED")
					// Fail closed for malicious proxies
					res.IsWorking = false
					res.Error = "HONEYPOT_DETECTED"
				}
			}
		} else {
			res.Error = err.Error()
		}
		output <- res
	}
}

// Helper to find free port and generate config
func setupSingbox(ctx context.Context, outboundJSON string) (*box.Box, int, error) {
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return nil, 0, err
	}
	port := l.Addr().(*net.TCPAddr).Port
	l.Close()

	configTemplate := `{
		"log": {"level": "panic"},
		"inbounds": [{"type": "mixed", "tag": "in", "listen": "127.0.0.1", "listen_port": %d}],
		"outbounds": [%s, {"type": "direct", "tag": "direct"}]
	}`
	configStr := fmt.Sprintf(configTemplate, port, outboundJSON)

	options, err := option.UnmarshalJSON([]byte(configStr))
	if err != nil {
		return nil, 0, err
	}

	instance, err := box.New(box.Options{Options: options, Context: ctx})
	if err != nil {
		return nil, 0, err
	}

	return instance, port, nil
}

// testLatency creates a temporary Sing-box instance to test the outbound
func testLatency(ctx context.Context, p ProxyInput) (float64, error) {
	instance, port, err := setupSingbox(ctx, p.Config)
	if err != nil {
		return 0, err
	}
	defer instance.Close()

	if err := instance.Start(); err != nil {
		return 0, err
	}

	// Give it a tiny moment to bind
	time.Sleep(50 * time.Millisecond)

	client := &http.Client{
		Timeout: TestTimeout,
		Transport: &http.Transport{
			Proxy: http.ProxyURL(&url.URL{
				Scheme: "socks5",
				Host:   fmt.Sprintf("127.0.0.1:%d", port),
			}),
		},
	}

	target := "https://www.google.com/generate_204"
	start := time.Now()
	resp, err := client.Get(target)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 204 && resp.StatusCode != 200 {
		return 0, fmt.Errorf("status %d", resp.StatusCode)
	}

	return float64(time.Since(start).Milliseconds()), nil
}

func isHoneypot(ctx context.Context, p ProxyInput) bool {
	// 1. Generate Token
	token := fmt.Sprintf("%d-%s", time.Now().UnixNano(), p.ID)

	// 2. Calculate Expected Signature locally
	secret := os.Getenv(HoneypotSecret)
	if secret == "" {
		return false // Cannot verify
	}

	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(token))
	expectedSig := hex.EncodeToString(mac.Sum(nil))

	// 3. Send to Canary via Proxy
	// We need to reuse the singbox instance?
	// Doing a separate start/stop for security check is safer but slower.
	// For batch mode, we accept the overhead for flagged proxies.

	instance, port, err := setupSingbox(ctx, p.Config)
	if err != nil {
		return false // Fail open? Or assume safe? Default safe to avoid blockage on error.
	}
	defer instance.Close()
	if err := instance.Start(); err != nil {
		return false
	}
	time.Sleep(50 * time.Millisecond)

	client := &http.Client{
		Timeout: 5 * time.Second,
		Transport: &http.Transport{
			Proxy: http.ProxyURL(&url.URL{Scheme: "socks5", Host: fmt.Sprintf("127.0.0.1:%d", port)}),
		},
	}

	target := fmt.Sprintf("%s?token=%s", CanaryURL, token)
	resp, err := client.Get(target)
	if err != nil {
		return false // Connection error, assume safe
	}
	defer resp.Body.Close()

	var r HoneypotResponse
	if err := json.NewDecoder(resp.Body).Decode(&r); err != nil {
		// If we get garbage instead of JSON, it might be an interception page
		return true
	}

	// 4. Verify
	if r.Signature != expectedSig {
		// Mismatch! Man-in-the-middle modified the request or replayed it?
		// Or the worker is returning wrong sig?
		// Mismatch = MALICIOUS.
		return true
	}

	return false
}
