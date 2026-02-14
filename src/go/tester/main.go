package main

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"configstream-tester/scanner"

	singbox "github.com/sagernet/sing-box"
	"github.com/sagernet/sing-box/option"
	"github.com/sagernet/sing/common/metadata"
)

// Request from Python (NDJSON)
type ProxyTestRequest struct {
	ID            string `json:"id"`
	ConfigStr     string `json:"config"`
	CheckHoneypot bool   `json:"check_honeypot"`
	Target        string `json:"target"`  // Optional override
	Timeout       int    `json:"timeout"` // Optional override
}

// Result to Python (NDJSON)
type ProxyTestResult struct {
	ID        string   `json:"id"`
	IsWorking bool     `json:"is_working"`
	Latency   int      `json:"latency"` // ms
	Error     string   `json:"error,omitempty"`
	Issues    []string `json:"issues,omitempty"`
}

// OutboundDialer interface to avoid direct dependency on internal sing-box types
type OutboundDialer interface {
	DialContext(ctx context.Context, network string, destination metadata.Socksaddr) (net.Conn, error)
}

var (
	workersFlag     int
	timeoutFlagRaw  string
	timeoutDuration time.Duration
	urlsFlag        string
	targetURLs      []string
	modeFlag        string
	limitFlag       int
)

func main() {
	flag.StringVar(&modeFlag, "mode", "test", "Operation mode: 'test' or 'scan'")
	flag.IntVar(&limitFlag, "limit", 50, "Limit for scan results")
	flag.IntVar(&workersFlag, "workers", 20, "Number of concurrent workers")
	flag.StringVar(&timeoutFlagRaw, "timeout", "10s", "Timeout duration (e.g. 10s or 10)")
	flag.StringVar(&urlsFlag, "urls", "http://cp.cloudflare.com", "Comma-separated list of target URLs")
	flag.Parse()

	// Parse timeout flag
	var err error
	timeoutDuration, err = time.ParseDuration(timeoutFlagRaw)
	if err != nil {
		// Try parsing as integer seconds
		if val, err2 := strconv.Atoi(timeoutFlagRaw); err2 == nil {
			timeoutDuration = time.Duration(val) * time.Second
		} else {
			log.Printf("Invalid timeout format '%s', defaulting to 10s", timeoutFlagRaw)
			timeoutDuration = 10 * time.Second
		}
	}
	if timeoutDuration < 1*time.Second {
		timeoutDuration = 1 * time.Second
	}

	// Sanitize workers flag
	if workersFlag < 1 {
		workersFlag = 1
	}
	if workersFlag > 200 {
		workersFlag = 200
	}

	// Sanitize URLs
	if urlsFlag != "" {
		raw := strings.Split(urlsFlag, ",")
		targetURLs = make([]string, 0, len(raw))
		for _, s := range raw {
			s = strings.TrimSpace(s)
			if s != "" {
				targetURLs = append(targetURLs, s)
			}
		}
	}

	log.SetOutput(os.Stderr)

	if modeFlag == "scan" {
		runScanner()
	} else {
		runTester()
	}
}

func runScanner() {
	resultsChan := make(chan scanner.ScanResult)

	go func() {
		scanner.RunScan(workersFlag, timeoutDuration, limitFlag, scanner.DefaultCidrs, resultsChan)
		close(resultsChan)
	}()

	encoder := json.NewEncoder(os.Stdout)
	count := 0

	for res := range resultsChan {
		if err := encoder.Encode(res); err != nil {
			log.Printf("Encode error: %v", err)
		}
		count++
		if limitFlag > 0 && count >= limitFlag {
			break
		}
	}
}

func runTester() {
	decoder := json.NewDecoder(os.Stdin)
	encoder := json.NewEncoder(os.Stdout)

	// Worker pool
	sem := make(chan struct{}, workersFlag)
	var wg sync.WaitGroup
	var outMu sync.Mutex

	decodeErrors := 0
	for {
		var req ProxyTestRequest
		if err := decoder.Decode(&req); err != nil {
			if err == io.EOF {
				break
			}
			log.Printf("Decode error: %v", err)
			decodeErrors++
			if decodeErrors >= 5 {
				log.Printf("Too many decode errors, stopping")
				break
			}
			continue
		}
		decodeErrors = 0

		sem <- struct{}{}
		wg.Add(1)
		go func(r ProxyTestRequest) {
			defer wg.Done()
			defer func() { <-sem }()

			res := testProxy(r)

			outMu.Lock()
			if err := encoder.Encode(res); err != nil {
				log.Printf("Encode error: %v", err)
			}
			outMu.Unlock()
		}(req)
	}

	wg.Wait()
}

func testProxy(req ProxyTestRequest) (result ProxyTestResult) {
	// Use named return so panic recovery can populate the ID field.
	// Previously, panic recovery returned zero-value ProxyTestResult{} with empty ID,
	// causing the Python side to never match the result and hang until timeout.
	result = ProxyTestResult{ID: req.ID, IsWorking: false}
	defer func() {
		if r := recover(); r != nil {
			log.Printf("PANIC in testProxy for %s: %v", req.ID, r)
			result.Error = "PANIC: " + fmt.Sprintf("%v", r)
		}
	}()

	start := time.Now()

	const maxConfigBytes = 1 << 20 // 1 MiB
	if len(req.ConfigStr) > maxConfigBytes {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Config too large"}
	}

	// parseConfig now returns ALL outbounds (supporting chains/detour).
	// Previously it returned only one outbound, discarding chain dependencies
	// and causing ALL chain/shield/revival testing to fail with "outbound not found".
	outbounds, proxyTag, err := parseConfig(req.ConfigStr)
	if err != nil {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Config parse error: " + err.Error()}
	}

	// Append the "direct" outbound that all configs need
	outbounds = append(outbounds, option.Outbound{
		Type: "direct",
		Tag:  "direct",
	})

	options := option.Options{
		Outbounds: outbounds,
		DNS: &option.DNSOptions{
			Servers: []option.DNSServerOptions{
				{
					Tag:     "google",
					Address: "8.8.8.8",
					Detour:  "direct",
				},
			},
		},
		Log: &option.LogOptions{
			Level: "error",
		},
	}
	_ = proxyTag // proxyTag is "proxy" (used for Router().Outbound lookup below)

	// Determine timeout (Request override > Global flag)
	timeout := timeoutDuration
	if req.Timeout > 0 {
		timeout = time.Duration(req.Timeout) * time.Second
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	instance, err := singbox.New(singbox.Options{
		Context: ctx,
		Options: options,
	})
	if err != nil {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Box init error: " + err.Error()}
	}

	if err := instance.Start(); err != nil {
		instance.Close()
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Box start error: " + err.Error()}
	}
	defer func() {
		// Recover panic during Close if any (defensive)
		defer func() {
			if r := recover(); r != nil {
				log.Printf("PANIC during instance.Close: %v", r)
			}
		}()
		instance.Close()
	}()

	// Determine target
	target := "http://cp.cloudflare.com"
	if req.Target != "" {
		target = req.Target
	} else if len(targetURLs) > 0 {
		target = targetURLs[0]
	}

	// Parse target URL robustly
	var dest metadata.Socksaddr
	var network = "tcp"
	var isHTTP = false
	var targetURL *url.URL

	if strings.HasPrefix(target, "tcp://") {
		network = "tcp"
		target = strings.TrimPrefix(target, "tcp://")
		dest = metadata.ParseSocksaddr(target)
	} else if strings.HasPrefix(target, "udp://") {
		network = "udp"
		target = strings.TrimPrefix(target, "udp://")
		dest = metadata.ParseSocksaddr(target)
	} else {
		// Use url.Parse
		// Ensure scheme exists for parser if missing
		parseTarget := target
		if !strings.Contains(parseTarget, "://") {
			// Scheme-less: Check if it's host:port (TCP) or URL-like (HTTP)
			if _, _, err := net.SplitHostPort(target); err == nil {
				// Has host and port, treat as TCP/UDP target
				dest = metadata.ParseSocksaddr(target)
				isHTTP = false
			} else {
				// Missing port or has path, treat as HTTP
				u, err := url.Parse("http://" + target)
				if err != nil || u.Host == "" {
					return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Invalid target format"}
				}
				targetURL = u

				hostPort := u.Host
				if _, _, err := net.SplitHostPort(hostPort); err != nil {
					// No explicit port: add defaults safely (works for IPv6 too).
					host := u.Hostname()
					port := "80"
					hostPort = net.JoinHostPort(host, port)
				}
				dest = metadata.ParseSocksaddr(hostPort)
				isHTTP = true
			}
		} else {
			u, err := url.Parse(target)
			if err == nil && u.Host != "" {
				targetURL = u
				hostPort := u.Host
				// Use net.SplitHostPort instead of string search for ":".
				// The old check `strings.Contains(hostPort, ":")` broke for IPv6
				// addresses like [::1] which contain ":" but have no port.
				if _, _, splitErr := net.SplitHostPort(hostPort); splitErr != nil {
					// No port present, add default based on scheme
					host := u.Hostname()
					switch u.Scheme {
					case "https":
						hostPort = net.JoinHostPort(host, "443")
					case "http":
						hostPort = net.JoinHostPort(host, "80")
					default:
						hostPort = net.JoinHostPort(host, "80")
					}
				}
				dest = metadata.ParseSocksaddr(hostPort)
				if u.Scheme == "http" || u.Scheme == "https" {
					isHTTP = true
				}
			} else {
				// Fallback
				dest = metadata.ParseSocksaddr(target)
			}
		}
	}

	if dest.AddrString() == "" || dest.Port == 0 {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Target parse error: invalid target"}
	}

	outbound, ok := instance.Router().Outbound("proxy")
	if !ok {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Proxy outbound not found"}
	}

	// Perform Connectivity Check
	if isHTTP {
		if targetURL == nil || targetURL.Host == "" {
			return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Invalid HTTP target"}
		}

		// HTTP Probe logic: use http.Client over proxy connection
		transport := &http.Transport{
			DialContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
				// addr is what http client wants to connect to (host:port)
				// We redirect this through our proxy outbound
				d := metadata.ParseSocksaddr(addr)
				return outbound.DialContext(ctx, network, d)
			},
			DisableKeepAlives:   true,
			ForceAttemptHTTP2:   false,
			TLSNextProto:        make(map[string]func(authority string, c *tls.Conn) http.RoundTripper),
			TLSHandshakeTimeout: 5 * time.Second,
		}
		defer transport.CloseIdleConnections()
		client := &http.Client{
			Transport: transport,
			Timeout:   timeout,
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				return http.ErrUseLastResponse
			},
		}

		reqHTTP, err := http.NewRequestWithContext(ctx, "GET", targetURL.String(), nil)
		if err != nil {
			return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "HTTP Request creation error: " + err.Error()}
		}

		resp, err := client.Do(reqHTTP)
		if err != nil {
			return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "HTTP GET error: " + err.Error()}
		}
		defer resp.Body.Close()
		_, _ = io.Copy(io.Discard, io.LimitReader(resp.Body, 32<<10))

		if resp.StatusCode < 200 || resp.StatusCode >= 400 {
			return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "HTTP status error: " + resp.Status}
		}
	} else {
		// Raw TCP/UDP Connect
		conn, err := outbound.DialContext(ctx, network, dest)
		if err != nil {
			return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Connect error: " + err.Error()}
		}
		defer conn.Close()

		if network == "udp" {
			_ = conn.SetDeadline(time.Now().Add(2 * time.Second))
			if _, err := conn.Write([]byte{0x00}); err != nil {
				return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "UDP write error: " + err.Error()}
			}
			var buf [1]byte
			udpTimeoutOK := false
			if _, err := conn.Read(buf[:]); err != nil {
				// Many UDP targets won't respond; a timeout is not necessarily a failure.
				if ne, ok := err.(net.Error); ok && ne.Timeout() {
					udpTimeoutOK = true
				} else {
					return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "UDP read error: " + err.Error()}
				}
			}
			_ = udpTimeoutOK
		}
	}

	latency := int(time.Since(start).Milliseconds())
	issues := []string{}

	if req.CheckHoneypot {
		if dialer, ok := outbound.(OutboundDialer); ok {
			hpTimeout := 3 * time.Second
			if ctx.Err() != nil {
				// Parent already canceled/expired; do not attempt honeypot probe.
			} else if deadline, ok := ctx.Deadline(); ok && time.Until(deadline) < hpTimeout {
				// Not enough time left in parent context; skip honeypot probe.
			} else {
				hpCtx, hpCancel := context.WithTimeout(ctx, hpTimeout)
				defer hpCancel()
				if isHoneypot(hpCtx, dialer) {
					issues = append(issues, "HONEYPOT")
				} else if hpCtx.Err() == context.DeadlineExceeded && ctx.Err() == nil {
					issues = append(issues, "HONEYPOT_TIMEOUT")
				}
			}
		}
	}

	return ProxyTestResult{
		ID:        req.ID,
		IsWorking: true,
		Latency:   latency,
		Issues:    issues,
	}
}

// parseConfig parses a config string and returns ALL outbounds plus the tag of
// the "entry point" outbound (the one the router should use as "proxy").
//
// Previously this returned a SINGLE outbound, discarding chain dependencies.
// For chain configs like [WARP -> VLESS], the VLESS outbound references WARP via
// its "detour" field. Returning only the VLESS outbound caused sing-box to fail
// with "outbound not found" because the WARP outbound it depends on was discarded.
// This was the ROOT CAUSE of all chain/shield/revival testing failing (0% success).
//
// Now returns ([]option.Outbound, proxyTag, error) so testProxy can insert ALL
// outbounds into the sing-box instance.
func parseConfig(configStr string) ([]option.Outbound, string, error) {
	if strings.TrimSpace(configStr) == "" {
		return nil, "", errors.New("empty config string")
	}

	// Helper: find the entry-point outbound tag in a slice.
	// Priority: explicit "proxy" tag > first non-infrastructure outbound.
	findEntryPoint := func(outs []option.Outbound) (string, bool) {
		for i := range outs {
			if outs[i].Tag == "proxy" && outs[i].Type != "" {
				return "proxy", true
			}
		}
		// No explicit "proxy" tag; pick the first usable outbound and rename it.
		for i := range outs {
			if outs[i].Type == "" {
				continue
			}
			switch outs[i].Type {
			case "direct", "block", "dns":
				continue
			}
			outs[i].Tag = "proxy"
			return "proxy", true
		}
		return "", false
	}

	// 0) Try: JSON array of outbounds (chain payloads from Python)
	var outs []option.Outbound
	if err := json.Unmarshal([]byte(configStr), &outs); err == nil && len(outs) > 0 {
		hasCandidate := false
		for i := range outs {
			if outs[i].Type != "" {
				hasCandidate = true
				break
			}
		}
		if hasCandidate {
			tag, ok := findEntryPoint(outs)
			if !ok {
				return nil, "", errors.New("no usable outbound found in config array")
			}
			return outs, tag, nil
		}
	}

	// 1) Try: single outbound JSON object
	var out option.Outbound
	if err := json.Unmarshal([]byte(configStr), &out); err == nil && out.Type != "" {
		out.Tag = "proxy"
		return []option.Outbound{out}, "proxy", nil
	}

	// 2) Try: full options object with outbounds
	var wrapper struct {
		Outbounds []option.Outbound `json:"outbounds"`
		Outbound  *option.Outbound  `json:"outbound"`
		Proxy     *option.Outbound  `json:"proxy"`
	}
	if err := json.Unmarshal([]byte(configStr), &wrapper); err != nil {
		return nil, "", err
	}

	switch {
	case wrapper.Proxy != nil && wrapper.Proxy.Type != "":
		wrapper.Proxy.Tag = "proxy"
		return []option.Outbound{*wrapper.Proxy}, "proxy", nil

	case wrapper.Outbound != nil && wrapper.Outbound.Type != "":
		wrapper.Outbound.Tag = "proxy"
		return []option.Outbound{*wrapper.Outbound}, "proxy", nil

	case len(wrapper.Outbounds) > 0:
		tag, ok := findEntryPoint(wrapper.Outbounds)
		if !ok {
			return nil, "", errors.New("no usable outbound found in outbounds")
		}
		return wrapper.Outbounds, tag, nil

	default:
		return nil, "", errors.New("no outbound found in config")
	}
}

func isHoneypot(ctx context.Context, dialer OutboundDialer) bool {
	dest := metadata.ParseSocksaddr("162.159.192.1:2408")
	conn, err := dialer.DialContext(ctx, "udp", dest)
	if err != nil {
		return false
	}
	defer conn.Close()

	packet := scanner.ConstructHandshakePacket()

	_, err = conn.Write(packet)
	if err != nil {
		return false
	}

	buf := make([]byte, 1024)
	// Check SetReadDeadline error to prevent indefinite blocking
	if err := conn.SetReadDeadline(time.Now().Add(2 * time.Second)); err != nil {
		return false
	}
	n, err := conn.Read(buf)
	if err != nil {
		return false
	}

	if n >= 4 {
		msgType := buf[0]
		switch msgType {
		case 2, 3, 4:
			// Valid WG response types (e.g., cookie/handshake-related)
			return false
		default:
			// Non-WG-looking response strongly suggests protocol mismatch/honeypot
			return true
		}
	}
	return false
}
