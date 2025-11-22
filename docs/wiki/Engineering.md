# Engineering Deep Dive

This section covers the algorithmic details of the ConfigStream engine.

## 1. Fuzzy Fingerprinting (Deduplication)

A major challenge in proxy aggregation is **Duplicate Pollution**. The same server (IP:Port) is often shared across 50 different Telegram channels, each adding a different "Remark" or "Title".

Simple string equality checks fail here.

### The Solution: `proxy_unique_key`

We generate a **Canonical Fingerprint** for every proxy:

```python
fingerprint = MD5(
    Protocol +
    Resolved_IP +
    Port +
    UUID +
    Transport_Path +
    SNI
)
```

*   We **ignore** mutable fields like `remarks`, `title`, or `date`.
*   We **resolve** domains to IPs first (where possible) to catch domains pointing to the same server.

This reduces our dataset size by ~40% while increasing quality density.

## 2. Scoring & Sorting

Proxies are not just "Working" or "Not Working". We rank them.

### The Priority Queue
1.  **Working Status:** Offline proxies are discarded immediately (unless in "Fallback Mode").
2.  **Latency (Ping):** Lower is better.
3.  **Jitter:** We penalize proxies with unstable latency (high standard deviation).
4.  **Uptime History:** A proxy that has been online for 7 days ranks higher than a new one, even if the new one is slightly faster.

### The "Chosen Top 1000"
We generate a premium subset called the **Chosen List**.
*   It selects the Top 50 proxies **per protocol** (VLESS, VMess, Trojan, SS).
*   It fills the rest with the globally fastest nodes.
*   This ensures protocol diversity so users aren't stuck if one protocol is blocked by their ISP.

## 3. Protocol Parsing

We support a wide range of modern censorship-resistant protocols:

*   **VLESS / VMess:** The standards. We support WS, gRPC, TCP, and HTTPUpgrade transports.
*   **Trojan:** With and without XTLS.
*   **Shadowsocks:** SIP002 and legacy formats.
*   **Hysteria2 / Tuic:** Newer UDP-based protocols (experimental support).

The parsers in `src/configstream/parsers/` are modular. They handle URL decoding, Base64 padding fixes, and query parameter extraction automatically.
