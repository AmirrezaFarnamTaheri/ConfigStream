package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"time"
    "net"
    "strings"
)

// Input structure (Proxy)
type ProxyTask struct {
    ID       string `json:"id"`
    Protocol string `json:"protocol"`
    Address  string `json:"address"`
    Port     int    `json:"port"`
    Config   string `json:"config"`
}

// Output structure
type TestResult struct {
	Type    string  `json:"type"` // "result", "log", "heartbeat"
	ID      string  `json:"id,omitempty"`
	Working bool    `json:"working,omitempty"`
	Latency float64 `json:"latency,omitempty"`
	Error   string  `json:"error,omitempty"`
	Message string  `json:"message,omitempty"`
    TS      int64   `json:"ts,omitempty"`
}

func main() {
    // Start Heartbeat (Required by Phase 6)
    go func() {
        ticker := time.NewTicker(10 * time.Second)
        for range ticker.C {
            msg := TestResult{
                Type: "heartbeat",
                TS:   time.Now().Unix(),
            }
            b, _ := json.Marshal(msg)
            fmt.Println(string(b))
        }
    }()

    // Read from Stdin (NDJSON)
    scanner := bufio.NewScanner(os.Stdin)
    for scanner.Scan() {
        line := scanner.Bytes()
        var task ProxyTask
        if err := json.Unmarshal(line, &task); err != nil {
            logError("JSON parse error", err.Error())
            continue
        }

        // Process Task
        // For now, we implement a basic TCP connect check if address/port available
        // to verify "aliveness" at network level.
        // Full protocol handshake would require importing sing-box core.
        go testProxy(task)
    }
}

func testProxy(task ProxyTask) {
    start := time.Now()

    // Address normalization
    addr := task.Address
    if strings.Contains(addr, ":") && !strings.Contains(addr, "[") {
        // IPv6?
        if strings.Count(addr, ":") > 1 {
            addr = "[" + addr + "]"
        }
    }
    target := fmt.Sprintf("%s:%d", addr, task.Port)

    conn, err := net.DialTimeout("tcp", target, 5*time.Second)
    if err != nil {
        emitResult(task.ID, false, 0, err.Error())
        return
    }
    conn.Close()

    latency := float64(time.Since(start).Milliseconds())
    emitResult(task.ID, true, latency, "")
}

func emitResult(id string, working bool, latency float64, errStr string) {
    res := TestResult{
        Type: "result",
        ID:   id,
        Working: working,
        Latency: latency,
        Error:   errStr,
    }
    b, _ := json.Marshal(res)
    fmt.Println(string(b))
}

func logError(msg, detail string) {
    res := TestResult{
        Type: "log",
        Message: msg + ": " + detail,
    }
    b, _ := json.Marshal(res)
    fmt.Println(string(b))
}
