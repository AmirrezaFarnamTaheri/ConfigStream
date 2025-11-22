## Phase 3: Smart Anti-Censorship

### Overview
This phase transforms simple proxies into advanced censorship-resistant chains.

### Exotic Chaining
Implemented in `src/configstream/output.py`.
- **Concept**: Relay (Hysteria/Tuic) -> Exit (VMess/Trojan).
- **Implementation**: `generate_exotic_chains` function creates Double-Hop Sing-box configurations.
- **Output**: `output/singbox-chains.json`

### Proxy Washing (Recycling)
Implemented in `src/configstream/output.py` and `src/configstream/testers.py`.
- **Concept**: "Dirty" proxies (Working but HTTP/SOCKS, or Google blocked) are wrapped in secure tunnels.
- **Method A**: SOCKS5 -> WARP WireGuard (Privacy Upgrade).
- **Method B**: HTTP -> TLS Proxy (Security Upgrade).
- **Implementation**:
    - `testers.py`: Tags proxies with `dirty_ip` or `insecure`.
    - `output.py`: `wash_dirty_proxies` function wraps them.

### Split Outputs
- **Tank**: `singbox-vpn.json` (TUN, FakeIP, Auto-Route)
- **Sniper**: `singbox.json` (Mixed Port, Fragmentation)
- **Diplomat**: `clash.yaml` (Conservative, standard)

## Phase 2: High-Performance Engine

### Go Batch Tester
- **Source**: `src/go/tester/main.go`
- **Architecture**: Single process, multiple goroutines.
- **Verification**: Signed Honeypot support.

### Docker Container
- **Dockerfile**: Multi-stage build (Go -> Python).
- **Registry**: `ghcr.io`
- **Pipeline**: Updated to run inside container.

## Phase 1: Distribution

### Fan-Out
- **Script**: `scripts/upload_telegram.py`, `scripts/upload_hf.py`
- **Pipeline**: Concurrent upload jobs.
- **Versioning**: Date-based tags.
