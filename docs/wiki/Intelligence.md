# Intelligence Layer

The Intelligence Layer transforms raw proxy data into high-value, resilient configurations. It is responsible for "Washing", Optimization, and Scoring.

## 1. Proxy Washing

### The Problem
Many high-speed proxies work perfectly but are blocked by destination sites (e.g., ChatGPT, Google) due to IP reputation ("Dirty IP").

### The Solution: WARP Chaining
ConfigStream "washes" these proxies by chaining them through Cloudflare WARP.
*   **Relay**: The user's high-speed proxy (Dirty IP).
*   **Exit**: Cloudflare WARP (Clean IP).

### How It Works
1.  **Identification**: Proxies flagged with `dirty_ip` or from high-censorship regions (IR, CN, RU) are selected.
2.  **Key Selection**: A valid WARP identity (`private_key`, `public_key`) is selected from the pool.
3.  **Endpoint Selection**: A "Clean IP" (WARP Endpoint) is chosen.
    *   **Active Scanning**: The system scans 162.159.x.x ranges for low-latency endpoints using `configstream-tester -mode scan`.
    *   **Fallback**: If scanning fails, it uses IRCFspace or GitHub Secrets (`WARP_CLEAN_IPS`).
4.  **Chaining**: A Sing-box `selector` or `urltest` chain is created: `User -> Relay -> WARP -> Internet`.

## 2. Geodesic Routing ("Smart Chains")

### The Concept
A straight line isn't always the fastest path in the internet topology. ConfigStream calculates optimal relay paths based on geography.

### Algorithm
1.  **Input**: User Region (Target), Proxy List.
2.  **Calculation**:
    *   Calculate distance from Origin to Relay.
    *   Calculate distance from Relay to Target.
    *   Minimize `Total Distance + Latency Penalty`.
3.  **Result**: A proxy in Germany might be chosen as the best relay for a user in Iran connecting to the US.

## 3. Anomaly Detection

### Subnet Flood Detection
If a single subnet (e.g., `/24`) provides 1000+ proxies, it's suspicious (likely a honeypot or ephemeral scan). The system down-ranks or caps these subnets.

### Jitter Analysis
The `AdaptiveTimeout` module tracks latency variance. High jitter (>2.0s variance) indicates an unstable proxy, lowering its score.
