package dnstester

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"net"
	"os/exec"
	"regexp"
	"strconv"
	"sync"
	"time"

	"github.com/miekg/dns"
)

// ScanResult holds the result of a DNS hijack scan
type ScanResult struct {
	IP         string `json:"ip"`
	IsHijacked bool   `json:"is_hijacked"`
	Latency    int64  `json:"latency_ms"`
	Reason     string `json:"reason,omitempty"`
}

// RunScan checks a list of IPs for DNS hijacking concurrently
func RunScan(ips []string, workers int) []ScanResult {
	results := make([]ScanResult, 0, len(ips))
	ipChan := make(chan string, len(ips))
	resChan := make(chan ScanResult, len(ips))
	var wg sync.WaitGroup

	// Start workers
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for ip := range ipChan {
				resChan <- CheckHijack(ip)
			}
		}()
	}

	// Feed workers
	for _, ip := range ips {
		ipChan <- ip
	}
	close(ipChan)

	// Close results channel when done
	go func() {
		wg.Wait()
		close(resChan)
	}()

	// Collect results
	for res := range resChan {
		results = append(results, res)
	}

	return results
}

// CheckHijack performs heuristics to detect if 8.8.8.8 (or other target) is hijacked
func CheckHijack(server string) ScanResult {
	res := ScanResult{IP: server}

	// 1. Basic DNS Connectivity & Latency
	// Use random subdomain to bypass cache (concept from dnsScanner.sh)
	randBytes := make([]byte, 4)
	rand.Read(randBytes)
	randomDomain := hex.EncodeToString(randBytes) + ".google.com."

	m := new(dns.Msg)
	m.SetQuestion(randomDomain, dns.TypeA)
	c := &dns.Client{Timeout: 2 * time.Second}

	_, rtt, err := c.Exchange(m, net.JoinHostPort(server, "53"))
	if err != nil {
		res.Latency = -1
		res.Reason = fmt.Sprintf("Unreachable: %v", err)
		return res
	}
	res.Latency = rtt.Milliseconds()

	// 2. Chaos Class Check (The "Cloudflare Trace" Trick)
	// Real Google DNS (8.8.8.8) does NOT support Chaos class queries for 'whoami.cloudflare'.
	// It should return REFUSED (5) or SERVFAIL (2).
	// If we get an answer, or NOERROR (0), it is likely intercepted by a middlebox.
	if isChaosHijacked(server) {
		res.IsHijacked = true
		res.Reason = "Responses to CHAOS TXT query (likely hijacked)"
		return res
	}

	// 3. RTT Comparison (ICMP vs DNS)
	// If DNS is suspiciously fast (<15ms) compared to ICMP (or absolute terms for cross-border),
	// it's a strong indicator of local interception.
	// Note: We only run ping if we have reasonable DNS latency to compare.
	if res.Latency < 20 {
		icmp, err := measurePingLatency(server)
		if err == nil {
			// If ICMP is significantly slower (e.g. > 50ms) while DNS is < 20ms
			if icmp > 50 {
				res.IsHijacked = true
				res.Reason = fmt.Sprintf("RTT Mismatch: DNS=%dms, ICMP=%dms", res.Latency, icmp)
				return res
			}
		}
	}

	return res
}

func isChaosHijacked(server string) bool {
	m := new(dns.Msg)
	m.SetQuestion("whoami.cloudflare.", dns.TypeTXT)
	m.Question[0].Qclass = dns.ClassCHAOS

	c := &dns.Client{Timeout: 2 * time.Second}
	in, _, err := c.Exchange(m, net.JoinHostPort(server, "53"))

	if err != nil {
		return false // Can't verify
	}

	// If we get an actual Answer record, it's definitely not Google
	if len(in.Answer) > 0 {
		return true
	}

	// If Rcode is Success (0), it's suspicious for Google (should be REFUSED/SERVFAIL)
	// Middleboxes often return Success with empty data.
	if in.Rcode == dns.RcodeSuccess {
		return true
	}

	return false
}

func measurePingLatency(server string) (int64, error) {
	// Simple shell ping. Works on Linux/Mac.
	// -c 1: count 1
	// -W 1: timeout 1s
	cmd := exec.Command("ping", "-c", "1", "-W", "1", server)
	out, err := cmd.Output()
	if err != nil {
		return 0, err
	}

	// Parse output
	output := string(out)
	re := regexp.MustCompile(`time=([\d\.]+)`)
	match := re.FindStringSubmatch(output)
	if len(match) > 1 {
		val, err := strconv.ParseFloat(match[1], 64)
		if err == nil {
			return int64(val), nil
		}
	}
	return 0, fmt.Errorf("no timing found")
}
