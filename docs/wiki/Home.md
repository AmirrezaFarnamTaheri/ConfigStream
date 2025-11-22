# Welcome to the ConfigStream Wiki

ConfigStream is not just a proxy aggregator; it is a **Network Intelligence Platform** designed to democratize access to the open internet.

This wiki serves as the "Zero to Hero" guide, covering everything from high-level architecture to low-level engineering details.

## 📚 Documentation Sections

### 1. [Architecture & Design](Architecture.md)
*   **The Hybrid Model:** Why we use Python for brains and Go for brawn.
*   **The Pipeline:** How a URL becomes a verified config in 6 stages.
*   **Sidecar Pattern:** Overcoming the GIL with `configstream-tester`.

### 2. [Security Engineering](Security.md)
*   **Zero-Trust Model:** We assume every proxy is malicious until proven otherwise.
*   **Proxy Washing:** Our proprietary tech to salvage "dirty" IPs using Cloudflare WARP.
*   **Honeypot Detection:** Active and Passive countermeasures against surveillance nodes.

### 3. [Engineering Deep Dive](Engineering.md)
*   **Fuzzy Fingerprinting:** How we deduplicate proxies even when they try to hide.
*   **Scoring Algorithms:** The math behind "High Quality" vs "Low Quality".
*   **Protocol Support:** VLESS, VMess, Trojan, Hysteria2, TUIC, and more.

### 4. [API & Data Reference](API_Reference.md)
*   **Output Schemas:** Structure of `metadata.json` and `summary.json`.
*   **Subscription Formats:** Details on Sing-box, Clash, and SIP008 outputs.

---

## 🚀 Quick Links

*   [GitHub Repository](https://github.com/AmirrezaFarnamTaheri/ConfigStream)
*   [Latest Release](https://github.com/AmirrezaFarnamTaheri/ConfigStream/releases)
*   [Issue Tracker](https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues)

## 🤝 Philosophy

**"Zero Budget, Infinite Scale."**
We rely 100% on free infrastructure (GitHub Actions, GitHub Pages). We do not use persistent databases or paid servers. The architecture is designed to be ephemeral, resilient, and horizontally scalable via CI/CD sharding.
