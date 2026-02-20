# Network Topology & Chaining

ConfigStream generates **Smart Chains** to optimize routing, improve reliability, and bypass censorship.

## Chaining Strategies

### 1. Simple Relay
`Client -> Entry Proxy -> Exit Proxy -> Internet`
- **Purpose**: Hides the Exit Proxy IP from the Client's ISP.
- **Use Case**: Accessing a sensitive Exit Proxy.

### 2. Washing Chain
`Client -> Proxy -> WARP -> Internet`
- **Purpose**: Gives the user a clean IP (Cloudflare) while using a potentially dirty Proxy.
- **Use Case**: Unblocking streaming services.

### 3. Shielded Chain (Gold)
`Client -> WARP (Clean IP) -> Proxy -> Internet`
- **Purpose**: Unblocks a blocked Proxy using WARP as a bridge.
- **Use Case**: Connecting to a blocked VMess/Trojan server.

## Smart Selection
ConfigStream uses geolocation (Haversine distance) and latency metrics to select optimal relay pairs (e.g. `US -> US` or `DE -> NL`) to minimize latency overhead.
