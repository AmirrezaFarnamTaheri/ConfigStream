# ConfigStream

**ConfigStream** is a high-performance, autonomous anti-censorship factory. It aggregates, validates, and distributes censorship-resistant proxy configurations (VLESS, VMess, Hysteria2, WireGuard) to users in restrictive network environments.

It operates on a **Zero Budget** model, utilizing GitHub Actions for compute, GitHub Pages for hosting, and GHCR for container distribution.

## 🚀 Features

*   **Massive Scale:** Tests 10,000+ proxies in minutes using a high-performance **Go Batch Tester**.
*   **Smart Unblocking:** Automatically wraps "dirty" proxies (blocked by Google/Netflix) in **Cloudflare WARP** or chains them through secure relays.
*   **Protocol Chaining:** Generates exotic chains (e.g., `Hysteria2 -> VMess`) to bypass advanced firewalls (GFW).
*   **Sanction-Proof Distribution:** "Fans out" releases to GitHub, Telegram, and Hugging Face simultaneously.
*   **Signed Honeypot:** verifying proxies are not Man-in-the-Middle attackers using cryptographic signatures.

## 🛠️ Architecture

The system is composed of three layers:

1.  **Core Logic (Python):** Orchestrates the pipeline, parses raw sources, and generates user configurations.
2.  **High-Performance Engine (Go):** A compiled sidecar that performs massive parallel connectivity checks and security verification.
3.  **Distribution Layer:** A "Fan-Out" system pushing artifacts to multiple mirrors.

See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

## 📦 Installation & Usage

### Local Development (Docker)

```bash
# Build the container
docker build -t configstream .

# Run the pipeline locally
docker run -it --rm -v $(pwd)/output:/app/output configstream python -m configstream.cli merge
```

### Bot Utilities

ConfigStream includes a CLI for bot automation and key generation:

```bash
# Generate WARP Keys for the recycling pool
python tools/bot_cli.py generate-warp --count 20
```

## 📂 Output Files

The pipeline generates specialized files for different users:

| File | Description | Best For |
| :--- | :--- | :--- |
| `singbox.json` | Standard config ("The Sniper") | Desktop, Browser Extensions |
| `singbox-vpn.json` | TUN/VPN Mode ("The Tank") | Android, iOS (Full Device) |
| `singbox-chains.json`| Experimental Chains | Bypassing GFW, Extreme Privacy |
| `clash.yaml` | Legacy Clash Config | Windows, Old Clients |
| `proxies.json` | Raw Master List | Developers, Researchers |

## 🛡️ Security

We employ a "Signed Honeypot" system to detect malicious proxies. See [SECURITY.md](docs/SECURITY.md) for details.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
