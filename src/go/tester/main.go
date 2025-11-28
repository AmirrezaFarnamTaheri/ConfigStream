package main

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	box "github.com/sagernet/sing-box"
	// [CRITICAL FIX 1] Register protocol modules so "mixed", "vless", etc. are recognized
	_ "github.com/sagernet/sing-box/include"
	"github.com/sagernet/sing-box/option"
)

// --- Configuration ---

const (
	MaxWorkers     = 20
	HoneypotSecret = "HONEYPOT_SECRET" // Env var
	// [OPTIMIZATION] Increased retries to handle port race conditions under load
	MaxRetries     = 15
)

var (
	TestTimeout = 10 * time.Second
	CanaryURL   = os.Getenv("CANARY_URL")
	rng         = rand.New(rand.NewSource(time.Now().UnixNano()))
	rngMu       sync.Mutex
	TestTargets = []string{
		"https://www.google.com/generate_204",
		"http://detectportal.firefox.com/success.txt",
		"https://www.microsoft.com/ncsi.txt",
		"http://cp.cloudflare.com/generate_204",
	}
)

// Thread-safe random int
func getRandomInt(n int) int {
	rngMu.Lock()
	defer rngMu.Unlock()
	return rng.Intn(n)
}

func getRandomTarget() string {
	rngMu.Lock()
	defer rngMu.Unlock()
	return TestTargets[rng.Intn(len(TestTargets))]
}

// --- Data Structures ---

type ProxyInput struct {
	Config        string `json:"config"`
	ID            string `json:"id"`
	CheckHoneypot bool   `json:"check_honeypot"`
}

type TestResult struct {
	ID        string   `json:"id"`
	IsWorking bool     `json:"is_working"`
	Latency   float64  `json:"latency"`
	Error     string   `json:"error,omitempty"`
	Issues    []string `json:"issues,omitempty"`
}

type HoneypotResponse struct {
	Signature string `json:"signature"`
}

// --- Main ---

func main() {
	workers := flag.Int("workers", MaxWorkers, "Number of concurrent workers")
	timeout := flag.Duration("timeout", 10*time.Second, "Timeout for each test")
	urls := flag.String("urls", "", "Comma-separated list of test URLs")
	flag.Parse()

	// [FIX] Force hard cap on workers regardless of flag to ensure stability
	if *workers > 25 {
		*workers = 25
		fmt.Fprintf(os.Stderr, "WARN: Capping workers to %d for stability\n", *workers)
	}

	TestTimeout = *timeout

	if *urls != "" {
		TestTargets = strings.Split(*urls, ",")
		for i := range TestTargets {
			TestTargets[i] = strings.TrimSpace(TestTargets[i])
		}
	}

	if CanaryURL == "" {
		fmt.Fprintln(os.Stderr, "Warning: CANARY_URL not set, honeypot checks are DISABLED")
	}

	// [LOG] Start info
	fmt.Fprintf(os.Stderr, "INFO: Starting Go Tester with %d workers, timeout %s\n", *workers, *timeout)

	inputChan := make(chan ProxyInput, *workers*2)
	outputChan := make(chan TestResult, *workers*2)

	var wg sync.WaitGroup

	for i := 0; i < *workers; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			worker(workerID, inputChan, outputChan)
		}(i)
	}

	go writer(outputChan)
	reader(inputChan)

	wg.Wait()
	close(outputChan)
	time.Sleep(100 * time.Millisecond)
	fmt.Fprintln(os.Stderr, "INFO: Go Tester shutting down")
}

func reader(inputChan chan<- ProxyInput) {
	// [CRITICAL FIX 2] Use json.Decoder instead of scanner to avoid 64KB token limit
	// and handle large configs safely.
	decoder := json.NewDecoder(os.Stdin)
	count := 0
	for {
		var p ProxyInput
		if err := decoder.Decode(&p); err != nil {
			if err == io.EOF {
				break
			}
			// Log decode errors but keep going to next object
			fmt.Fprintf(os.Stderr, "ERROR: JSON Decode error: %v\n", err)
			continue
		}
		inputChan <- p
		count++
	}
	fmt.Fprintf(os.Stderr, "INFO: Read %d proxies from input\n", count)
	close(inputChan)
}

func writer(outputChan <-chan TestResult) {
	encoder := json.NewEncoder(os.Stdout)
	count := 0
	for res := range outputChan {
		if err := encoder.Encode(res); err != nil {
			fmt.Fprintln(os.Stderr, "ERROR: Encode error:", err)
		}
		count++
	}
	fmt.Fprintf(os.Stderr, "INFO: Wrote %d results\n", count)
}

func worker(id int, input <-chan ProxyInput, output chan<- TestResult) {
	ctx := context.Background()

	// Global worker panic handler
	defer func() {
		if r := recover(); r != nil {
			fmt.Fprintf(os.Stderr, "CRITICAL WORKER %d PANIC: %v\n", id, r)
		}
	}()

	for p := range input {
		// Per-task panic handler to keep worker alive
		func() {
			defer func() {
				if r := recover(); r != nil {
					output <- TestResult{
						ID: p.ID,
						IsWorking: false,
						Error: fmt.Sprintf("PANIC: %v", r),
					}
				}
			}()

			res := TestResult{ID: p.ID}
			// Add random jitter before starting to desynchronize port binding
			time.Sleep(time.Duration(getRandomInt(50)) * time.Millisecond)

			latency, issues, err := testLatency(ctx, p)

			if err == nil {
				res.IsWorking = true
				res.Latency = latency
				if len(issues) > 0 {
					res.Issues = append(res.Issues, issues...)
				}

				if p.CheckHoneypot && CanaryURL != "" {
					if isHoneypot(ctx, p) {
						res.Issues = append(res.Issues, "HONEYPOT_DETECTED")
						res.IsWorking = false
						res.Error = "HONEYPOT_DETECTED"
					}
				}
			} else {
				res.Error = err.Error()
				// [LOG] Debug logging for failures (optional, maybe verbose)
				// fmt.Fprintf(os.Stderr, "DEBUG: Proxy %s failed: %v\n", p.ID, err)
			}
			output <- res
		}()
	}
}

func setupSingbox(ctx context.Context, outboundJSON string) (*box.Box, int, error) {
	var lastErr error

	for i := 0; i < MaxRetries; i++ {
		// [FIX 2] Jitter Retry: Sleep randomly to avoid port collision storms
		if i > 0 {
			time.Sleep(time.Duration(getRandomInt(150)+50) * time.Millisecond)
		}

		// [CRITICAL FIX] Do NOT use net.Listen to check ports. It creates a race condition.
		// Just pick a random port and let Sing-box try to bind it.
		// Range: 20000 - 60000
		port := 20000 + getRandomInt(40000)

		// [CRITICAL FIX] Changed inbound type from "mixed" to "socks" to avoid "missing endpoint registry"
		// error in sing-box v1.12+. The tester only uses SOCKS5 anyway.
		configTemplate := `{
			"log": {"level": "panic"},
			"dns": {"servers": []},
			"inbounds": [{"type": "socks", "tag": "in", "listen": "127.0.0.1", "listen_port": %d}],
			"outbounds": [%s, {"type": "direct", "tag": "direct"}]
		}`
		configStr := fmt.Sprintf(configTemplate, port, outboundJSON)

		var opts option.Options
		// [CRITICAL FIX] Use standard json.Unmarshal to utilize the global type registry
		err := json.Unmarshal([]byte(configStr), &opts)
		if err != nil {
			// Config error (permanent), don't retry
			fmt.Fprintf(os.Stderr, "ERROR: Invalid config JSON for port %d: %v\n", port, err)
			return nil, 0, err
		}

		// [CRITICAL FIX] Do not pass context explicitly to rely on box.New default initialization
		// which correctly sets up the registry in the context it creates/uses.
		// If we passed 'ctx' (which is just context.Background), we'd need to manually inject registries.
		boxOpts := box.Options{
			Options: opts,
		}
		instance, err := box.New(boxOpts)
		if err != nil {
			// [FIX] Abort immediately on configuration/parse errors (e.g., missing uTLS)
			if strings.Contains(err.Error(), "parse outbound") || strings.Contains(err.Error(), "unknown field") {
				return nil, 0, err
			}
			lastErr = err
			// fmt.Fprintf(os.Stderr, "WARN: box.New failed (attempt %d): %v\n", i+1, err)
			continue
		}

		err = instance.Start()
		if err != nil {
			instance.Close()
			// [FIX] Abort if error indicates a fatal config issue not caught by New
			if strings.Contains(err.Error(), "not included in this build") {
				return nil, 0, err
			}
			lastErr = err
			// fmt.Fprintf(os.Stderr, "WARN: instance.Start failed (attempt %d): %v\n", i+1, err)
			continue
		}

		return instance, port, nil
	}

	return nil, 0, fmt.Errorf("failed to bind port after %d retries: %v", MaxRetries, lastErr)
}

func testLatency(ctx context.Context, p ProxyInput) (float64, []string, error) {
	instance, port, err := setupSingbox(ctx, p.Config)
	if err != nil {
		return 0, nil, err
	}
	defer instance.Close()

	// [OPTIMIZATION] Reduced sleep time. Start() is usually synchronous enough.
	time.Sleep(10 * time.Millisecond)

	// [CRITICAL] Ensure the transport forces resolution via the proxy if needed.
	proxyURL, _ := url.Parse(fmt.Sprintf("socks5://127.0.0.1:%d", port))

	client := &http.Client{
		Timeout: TestTimeout,
		Transport: &http.Transport{
			Proxy: http.ProxyURL(proxyURL),
			// [OPTIMIZATION] Disable keep-alives to prevent FD exhaustion on localhost
			DisableKeepAlives: true,
		},
	}

	var issues []string
	// [FIX] Random target selection to avoid rate limiting
	target := getRandomTarget()
	start := time.Now()
	resp, err := client.Get(target)

	success := false
	if err == nil {
		defer resp.Body.Close()
		io.Copy(io.Discard, resp.Body)
		if resp.StatusCode == 204 || resp.StatusCode == 200 {
			success = true
		} else {
			// [LOG] Info about status code failure
			// fmt.Fprintf(os.Stderr, "DEBUG: Target %s returned status %d\n", target, resp.StatusCode)
		}
	} else {
		// [LOG] Info about connection error
		// fmt.Fprintf(os.Stderr, "DEBUG: Target %s failed: %v\n", target, err)
	}

	if success {
		return float64(time.Since(start).Milliseconds()), nil, nil
	}

	// Fallback to a different target (simple retries with random selection again or fixed fallback)
	target2 := getRandomTarget()
	if target2 == target && len(TestTargets) > 1 {
		// Try to pick a different one
		for {
			target2 = getRandomTarget()
			if target2 != target {
				break
			}
		}
	}

	start = time.Now()
	resp, err = client.Get(target2)

	if err != nil {
		return 0, nil, err
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)

	if resp.StatusCode == 204 || resp.StatusCode == 200 {
		return float64(time.Since(start).Milliseconds()), issues, nil
	}

	return 0, nil, fmt.Errorf("all targets failed")
}

func isHoneypot(ctx context.Context, p ProxyInput) bool {
	token := fmt.Sprintf("%d-%s", time.Now().UnixNano(), p.ID)
	secret := os.Getenv(HoneypotSecret)
	if secret == "" {
		return false
	}

	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(token))
	expectedSig := hex.EncodeToString(mac.Sum(nil))

	instance, port, err := setupSingbox(ctx, p.Config)
	if err != nil {
		return false
	}
	defer instance.Close()

	time.Sleep(10 * time.Millisecond)

	proxyURL, _ := url.Parse(fmt.Sprintf("socks5://127.0.0.1:%d", port))
	client := &http.Client{
		Timeout: 5 * time.Second,
		Transport: &http.Transport{
			Proxy:             http.ProxyURL(proxyURL),
			DisableKeepAlives: true,
		},
	}

	target := fmt.Sprintf("%s?token=%s", CanaryURL, token)
	resp, err := client.Get(target)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	var r HoneypotResponse
	if err := json.NewDecoder(resp.Body).Decode(&r); err != nil {
		return true
	}

	if r.Signature != expectedSig {
		return true
	}

	return false
}
