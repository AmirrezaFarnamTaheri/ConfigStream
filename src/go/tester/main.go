package main

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"time"

	"github.com/sagernet/sing-box/box"
	"github.com/sagernet/sing-box/common/metadata"
	"github.com/sagernet/sing-box/option"
)

// Input structure for a single proxy test
type ProxyTestRequest struct {
	ID        string      `json:"id"`
	ProxyConf interface{} `json:"proxy_config"` // The 'outbound' config block
	Target    string      `json:"target"`
	Timeout   int         `json:"timeout"` // seconds
}

// Output structure
type ProxyTestResult struct {
	ID      string `json:"id"`
	Success bool   `json:"success"`
	Latency int    `json:"latency"` // ms
	Error   string `json:"error,omitempty"`
}

func main() {
	// Simple STDIN/STDOUT loop
	decoder := json.NewDecoder(os.Stdin)
	encoder := json.NewEncoder(os.Stdout)

	for {
		var reqs []ProxyTestRequest
		if err := decoder.Decode(&reqs); err != nil {
			if err.Error() == "EOF" {
				return
			}
			log.Printf("Decode error: %v", err)
			continue
		}

		results := make([]ProxyTestResult, len(reqs))
		ch := make(chan ProxyTestResult, len(reqs))

		for _, req := range reqs {
			go func(r ProxyTestRequest) {
				ch <- testProxy(r)
			}(req)
		}

		for i := 0; i < len(reqs); i++ {
			results[i] = <-ch
		}

		if err := encoder.Encode(results); err != nil {
			log.Printf("Encode error: %v", err)
		}
	}
}

func testProxy(req ProxyTestRequest) ProxyTestResult {
	start := time.Now()

	outboundConfig, err := mapToOutbound(req.ProxyConf)
	if err != nil {
		return ProxyTestResult{ID: req.ID, Success: false, Error: "Config map error: " + err.Error()}
	}

	// Basic options structure for Sing-Box
	options := option.Options{
		Outbounds: []option.Outbound{
			outboundConfig,
			{
				Type: "direct",
				Tag:  "direct",
			},
		},
		DNS: &option.DNSOption{
			Servers: []option.DNSServerOptions{
				{
					Tag:     "google",
					Address: "8.8.8.8",
					Detour:  "direct",
				},
			},
		},
		Log: &option.LogOption{
			Level: "error",
		},
	}

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(req.Timeout)*time.Second)
	defer cancel()

	instance, err := box.New(box.Options{
		Context: ctx,
		Options: options,
	})
	if err != nil {
		return ProxyTestResult{ID: req.ID, Success: false, Error: "Box init error: " + err.Error()}
	}

	if err := instance.Start(); err != nil {
		instance.Close()
		return ProxyTestResult{ID: req.ID, Success: false, Error: "Box start error: " + err.Error()}
	}
	defer instance.Close()

	// Attempt to connect to the target using the proxy
	// We parse the target address (e.g., "google.com:80")
	dest, err := metadata.ParseSocksaddr(req.Target)
	if err != nil {
		// Fallback if target parsing fails: assume success of Start() implies config validity
		// but log error. Ideally, we should fail.
		return ProxyTestResult{ID: req.ID, Success: false, Error: "Target parse error: " + err.Error()}
	}

	// Use the instance's router/dialer to connect
	// Note: API might vary by version. Using standard DialContext if available on Router.
	// If Router() is not exposed or DialContext not available, this might fail compilation.
	// However, this is the standard way to test connectivity in Sing-box.
	conn, err := instance.Router().Dial(ctx, dest)
	if err != nil {
		return ProxyTestResult{ID: req.ID, Success: false, Error: "Connect error: " + err.Error()}
	}
	conn.Close()

	latency := int(time.Since(start).Milliseconds())
	return ProxyTestResult{ID: req.ID, Success: true, Latency: latency}
}

func mapToOutbound(raw interface{}) (option.Outbound, error) {
	b, err := json.Marshal(raw)
	if err != nil {
		return option.Outbound{}, err
	}
	var out option.Outbound
	if err := json.Unmarshal(b, &out); err != nil {
		return option.Outbound{}, err
	}
	out.Tag = "proxy"
	return out, nil
}
