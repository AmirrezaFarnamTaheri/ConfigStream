package main

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"time"

	"github.com/sagernet/sing-box"
	"github.com/sagernet/sing/common/metadata"
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
	dest := metadata.ParseSocksaddr(req.Target)

	// Use the instance's router/dialer to connect
	outbound, ok := instance.Router().Outbound("proxy")
	if !ok {
		return ProxyTestResult{ID: req.ID, Success: false, Error: "Proxy outbound not found"}
	}

	conn, err := outbound.DialContext(ctx, "tcp", dest)
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
