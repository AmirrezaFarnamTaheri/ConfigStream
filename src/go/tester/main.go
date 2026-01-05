package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
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
)

func main() {
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

func testProxy(req ProxyTestRequest) ProxyTestResult {
	start := time.Now()

	const maxConfigBytes = 1 << 20 // 1 MiB
	if len(req.ConfigStr) > maxConfigBytes {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Config too large"}
	}

	outboundConfig, err := parseConfig(req.ConfigStr)
	if err != nil {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Config parse error: " + err.Error()}
	}

	options := option.Options{
		Outbounds: []option.Outbound{
			outboundConfig,
			{
				Type: "direct",
				Tag:  "direct",
			},
		},
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
	defer instance.Close()

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
				if !strings.Contains(hostPort, ":") {
					switch u.Scheme {
					case "https":
						hostPort += ":443"
					case "http":
						hostPort += ":80"
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
			if _, err := conn.Read(buf[:]); err != nil {
				// Many UDP targets won't respond; a timeout is not necessarily a failure.
				if ne, ok := err.(net.Error); ok && ne.Timeout() {
					return ProxyTestResult{ID: req.ID, IsWorking: true, Latency: int(time.Since(start).Milliseconds())}
				}
				return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "UDP read error: " + err.Error()}
			}
		}
	}

	latency := int(time.Since(start).Milliseconds())
	issues := []string{}

	if req.CheckHoneypot {
		if dialer, ok := outbound.(OutboundDialer); ok {
			hpTimeout := 3 * time.Second
			if deadline, ok := ctx.Deadline(); ok && time.Until(deadline) < hpTimeout {
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

func parseConfig(configStr string) (option.Outbound, error) {
	if strings.TrimSpace(configStr) == "" {
		return option.Outbound{}, errors.New("empty config string")
	}

	// 0) Try: JSON array of outbounds (batch/chain payloads)
	var outs []option.Outbound
	if err := json.Unmarshal([]byte(configStr), &outs); err == nil {
		hasCandidate := false
		for i := range outs {
			if outs[i].Type != "" {
				hasCandidate = true
				break
			}
		}
		if hasCandidate {
			for i := range outs {
				if outs[i].Type == "" {
					continue
				}
				if outs[i].Tag == "proxy" {
					// Ensure canonical tag without mutating unrelated entries.
					out := outs[i]
					out.Tag = "proxy"
					return out, nil
				}
			}
			for i := range outs {
				if outs[i].Type == "" {
					continue
				}
				switch outs[i].Type {
				case "direct", "block", "dns":
					continue
				}
				out := outs[i]
				out.Tag = "proxy"
				return out, nil
			}
			return option.Outbound{}, errors.New("no usable outbound found in config array")
		}
	}

	// 1) Try: single outbound JSON object
	var out option.Outbound
	if err := json.Unmarshal([]byte(configStr), &out); err == nil && out.Type != "" {
		out.Tag = "proxy"
		return out, nil
	}

	// 2) Try: full options object with outbounds
	var wrapper struct {
		Outbounds []option.Outbound `json:"outbounds"`
		Outbound  *option.Outbound  `json:"outbound"`
		Proxy     *option.Outbound  `json:"proxy"`
	}
	if err := json.Unmarshal([]byte(configStr), &wrapper); err != nil {
		return option.Outbound{}, err
	}

	switch {
	case wrapper.Proxy != nil && wrapper.Proxy.Type != "":
		wrapper.Proxy.Tag = "proxy"
		return *wrapper.Proxy, nil

	case wrapper.Outbound != nil && wrapper.Outbound.Type != "":
		wrapper.Outbound.Tag = "proxy"
		return *wrapper.Outbound, nil

	case len(wrapper.Outbounds) > 0:
		// Prefer explicit "proxy" tag if present.
		for i := range wrapper.Outbounds {
			if wrapper.Outbounds[i].Type == "" {
				continue
			}
			if wrapper.Outbounds[i].Tag == "proxy" {
				out := wrapper.Outbounds[i]
				out.Tag = "proxy"
				return out, nil
			}
		}
		// Otherwise pick the first valid outbound.
		for i := range wrapper.Outbounds {
			if wrapper.Outbounds[i].Type == "" {
				continue
			}
			out := wrapper.Outbounds[i]
			out.Tag = "proxy"
			return out, nil
		}
		return option.Outbound{}, errors.New("no outbound found in outbounds")

	default:
		return option.Outbound{}, errors.New("no outbound found in config")
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
	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
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
