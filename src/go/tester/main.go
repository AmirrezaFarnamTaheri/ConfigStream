package main

import (
	"context"
	"encoding/json"
	"flag"
	"io"
	"log"
	"net"
	"os"
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
	Target        string `json:"target"` // Optional override
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
	workersFlag int
	timeoutFlag int
	urlsFlag    string
	targetURLs  []string
)

func main() {
	flag.IntVar(&workersFlag, "workers", 20, "Number of concurrent workers")
	flag.IntVar(&timeoutFlag, "timeout", 10, "Timeout in seconds")
	flag.StringVar(&urlsFlag, "urls", "http://cp.cloudflare.com", "Comma-separated list of target URLs")
	flag.Parse()

	if urlsFlag != "" {
		targetURLs = strings.Split(urlsFlag, ",")
	}

	log.SetOutput(os.Stderr)

	decoder := json.NewDecoder(os.Stdin)
	encoder := json.NewEncoder(os.Stdout)

	// Worker pool
	sem := make(chan struct{}, workersFlag)
	var wg sync.WaitGroup
	var outMu sync.Mutex

	for {
		var req ProxyTestRequest
		if err := decoder.Decode(&req); err != nil {
			if err == io.EOF {
				break
			}
			log.Printf("Decode error: %v", err)
			continue
		}

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
	timeoutVal := timeoutFlag
	if req.Timeout > 0 {
		timeoutVal = req.Timeout
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutVal)*time.Second)
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

	// Parse network and address
	network := "tcp"
	if strings.HasPrefix(target, "tcp://") {
		network = "tcp"
		target = strings.TrimPrefix(target, "tcp://")
	} else if strings.HasPrefix(target, "udp://") {
		network = "udp"
		target = strings.TrimPrefix(target, "udp://")
	}

	// Handle simple http/https prefix stripping for Socksaddr parsing
	if strings.HasPrefix(target, "http://") {
		target = strings.TrimPrefix(target, "http://")
		if !strings.Contains(target, ":") {
			target += ":80"
		}
	} else if strings.HasPrefix(target, "https://") {
		target = strings.TrimPrefix(target, "https://")
		if !strings.Contains(target, ":") {
			target += ":443"
		}
	}

	dest := metadata.ParseSocksaddr(target)
	if dest.AddrString() == "" || dest.Port == 0 {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Target parse error: invalid target"}
	}

	outbound, ok := instance.Router().Outbound("proxy")
	if !ok {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Proxy outbound not found"}
	}

	conn, err := outbound.DialContext(ctx, network, dest)
	if err != nil {
		return ProxyTestResult{ID: req.ID, IsWorking: false, Error: "Connect error: " + err.Error()}
	}
	conn.Close()

	latency := int(time.Since(start).Milliseconds())
	issues := []string{}

	if req.CheckHoneypot {
		if dialer, ok := outbound.(OutboundDialer); ok {
			if isHoneypot(ctx, dialer) {
				issues = append(issues, "HONEYPOT")
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
	var out option.Outbound
	if err := json.Unmarshal([]byte(configStr), &out); err != nil {
		return option.Outbound{}, err
	}
	out.Tag = "proxy"
	return out, nil
}

func isHoneypot(ctx context.Context, outbound OutboundDialer) bool {
	dest := metadata.ParseSocksaddr("162.159.192.1:2408")
	conn, err := outbound.DialContext(ctx, "udp", dest)
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

	if n >= 32 {
		msgType := buf[0]
		if msgType == 2 || msgType == 3 || msgType == 4 {
			return false
		}
	}
	return false
}
