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
	"math/rand"
	"net"
	"net/http"
	"net/url"
	"os"
	"sync"
	"time"

	box "github.com/sagernet/sing-box"
	"github.com/sagernet/sing-box/option"
)

// --- Configuration ---

const (
	MaxWorkers     = 50
	TestTimeout    = 10 * time.Second
	HoneypotSecret = "HONEYPOT_SECRET" // Env var
	MaxRetries     = 3
)

var (
	CanaryURL = os.Getenv("CANARY_URL")
	// Use local random source to avoid global lock contention and deprecation warnings
	rng   = rand.New(rand.NewSource(time.Now().UnixNano()))
	rngMu sync.Mutex
)

// Thread-safe random int
func getRandomInt(n int) int {
	rngMu.Lock()
	defer rngMu.Unlock()
	return rng.Intn(n)
}

// --- Data Structures ---

type ProxyInput struct {
	Config        string `json:"config"` // Full Sing-box outbound JSON
	ID            string `json:"id"`
	CheckHoneypot bool   `json:"check_honeypot"`
}

type TestResult struct {
	ID        string   `json:"id"`
	IsWorking bool     `json:"is_working"`
	Latency   float64  `json:"latency"` // milliseconds
	Error     string   `json:"error,omitempty"`
	Issues    []string `json:"issues,omitempty"` // e.g. ["HONEYPOT_DETECTED", "DIRTY_IP"]
}

type HoneypotResponse struct {
	Signature string `json:"signature"`
}

// --- Main ---

func main() {
	workers := flag.Int("workers", MaxWorkers, "Number of concurrent workers")
	flag.Parse()

	if CanaryURL == "" {
		// Warn loudly but proceed – this disables active honeypot detection
		// while still allowing performance testing.
		fmt.Fprintln(os.Stderr, "Warning: CANARY_URL not set, honeypot checks are DISABLED")
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
		latency, issues, err := testLatency(ctx, p)

		if err == nil {
			res.IsWorking = true
			res.Latency = latency
			if len(issues) > 0 {
				res.Issues = append(res.Issues, issues...)
			}

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
// Implements a retry loop to handle race conditions
func setupSingbox(ctx context.Context, outboundJSON string) (*box.Box, int, error) {
	var lastErr error

	for i := 0; i < MaxRetries; i++ {
		// 1. Get a random free port
		l, err := net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			lastErr = err
			time.Sleep(time.Duration(getRandomInt(50)) * time.Millisecond)
			continue
		}
		port := l.Addr().(*net.TCPAddr).Port
		l.Close() // Release it

		// 2. Configure Sing-box
		configTemplate := `{
			"log": {"level": "panic"},
			"inbounds": [{"type": "mixed", "tag": "in", "listen": "127.0.0.1", "listen_port": %d}],
			"outbounds": [%s, {"type": "direct", "tag": "direct"}]
		}`
		configStr := fmt.Sprintf(configTemplate, port, outboundJSON)

		var opts option.Options
		err = opts.UnmarshalJSONContext(ctx, []byte(configStr))
		if err != nil {
			return nil, 0, err
		}

		// 3. Try to start
		boxOpts := box.Options{
			Options: opts,
			Context: ctx,
		}
		instance, err := box.New(boxOpts)
		if err != nil {
			lastErr = err
			// Check if it's an address in use error (generic check)
			// box.New might not bind immediately, but usually it prepares listeners.
			// Actually instance.Start() is what binds.
			// But we return instance here to let caller start.
			// Wait, the caller starts it. If Start() fails, we need to retry the whole flow.
			// So we must move Start() inside here or return a closure?
			// The original code returned instance, port.
			// To robustly retry, we should probably Start it here.

			// Let's modify this function to Start the instance as well.
			continue
		}

		err = instance.Start()
		if err != nil {
			instance.Close()
			lastErr = err
			// Retry on bind error
			time.Sleep(time.Duration(getRandomInt(50)) * time.Millisecond)
			continue
		}

		return instance, port, nil
	}

	return nil, 0, fmt.Errorf("failed to bind port after %d retries: %v", MaxRetries, lastErr)
}

// testLatency creates a temporary Sing-box instance to test the outbound
func testLatency(ctx context.Context, p ProxyInput) (float64, []string, error) {
	// setupSingbox now Starts the instance
	instance, port, err := setupSingbox(ctx, p.Config)
	if err != nil {
		return 0, nil, err
	}
	defer instance.Close()

	// Give it a tiny moment to bind - though Start() is synchronous for binding usually.
	// But network stack might lag.
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

	var issues []string

	// 1. Try Google (Gold Standard)
	target := "https://www.google.com/generate_204"
	start := time.Now()
	resp, err := client.Get(target)

	success := false
	if err == nil {
		defer resp.Body.Close()
		// Drain body to be polite
		io.Copy(io.Discard, resp.Body)
		if resp.StatusCode == 204 || resp.StatusCode == 200 {
			success = true
		}
	}

	if success {
		return float64(time.Since(start).Milliseconds()), nil, nil
	}

	// 2. Try Cloudflare (Fallback)
	// If Google failed, we try a non-blocked target to see if the proxy is alive but "Dirty"
	target = "http://cp.cloudflare.com/generate_204"
	start = time.Now() // Restart timer for fair latency measurement to the working target
	resp, err = client.Get(target)

	if err != nil {
		return 0, nil, err
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)

	if resp.StatusCode == 204 || resp.StatusCode == 200 {
		// Proxy is working, but blocked by Google
		issues = append(issues, "DIRTY_IP")
		return float64(time.Since(start).Milliseconds()), issues, nil
	}

	return 0, nil, fmt.Errorf("all targets failed")
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
	instance, port, err := setupSingbox(ctx, p.Config)
	if err != nil {
		return false // Fail open? Or assume safe? Default safe to avoid blockage on error.
	}
	defer instance.Close()
	// setupSingbox already started it

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
		// Mismatch = MALICIOUS.
		return true
	}

	return false
}
