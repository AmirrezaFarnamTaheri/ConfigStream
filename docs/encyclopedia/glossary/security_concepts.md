# Security Concepts

### Circuit Breaker
A design pattern used in the pipeline. If a source or tester fails repeatedly (e.g. 5 timeouts in a row), the "Circuit Breaker" trips, temporarily disabling that component to prevent resource exhaustion and cascading failures.

### Fail-Open vs Fail-Safe
- **Fail-Open**: If a security check fails (e.g. Blocklist API down), allow the traffic. (ConfigStream uses this for non-critical checks to ensure availability).
- **Fail-Safe**: If a check fails, block the traffic. (ConfigStream uses this for critical parsing/validation).

### Active Probing
When a censor connects to your proxy server to see if it responds like a proxy. If it does, the IP is blocked. Protocols like VLESS-Reality and Trojan fallback to a real website to defeat this.

### Steganography
Hiding data within other data. ConfigStream uses steganography (hiding config data in images) for secure distribution.
