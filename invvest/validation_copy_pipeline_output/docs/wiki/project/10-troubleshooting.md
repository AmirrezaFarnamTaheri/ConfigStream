# 10. Troubleshooting & FAQ

## Common Issues

### 1. "Configuration Import Failed"
If your client fails to import the configuration:
*   **Check the Format**: Ensure you are using the correct format for your client (e.g., `.yaml` for Clash, `.json` for Sing-box).
*   **Base64 Decoding**: Some older clients expect raw URI lists. Try decoding the Base64 string manually if your client doesn't support subscription links.
*   **Update Client**: We use modern protocols (VLESS-Reality, Hysteria2). Ensure your client is up to date (e.g., v2rayNG >= 1.8.5, Sing-box >= 1.8).

### 2. "Connected but No Internet"
*   **Time Sync**: VLESS/VMess protocols require your device time to be accurate within 90 seconds. Sync your clock.
*   **Geo-Blocking**: The proxy might be blocked by the destination site. Try a different country.
*   **ISP Blocking**: Your ISP might be blocking the specific port or protocol. Try a "Washed" proxy or a different protocol (e.g., switch from VLESS to Hysteria).

### 3. "High Latency"
*   **Real vs. Handshake**: The latency shown in the app is often just the TCP handshake time to the proxy server, not the real download speed.
*   **Route Optimization**: Use the "Auto" or "UrlTest" group in your client to automatically select the fastest node.

## Client-Specific Guides

### Android
*   **v2rayNG**: Recommended. Supports all protocols.
    1.  Copy the "Universal Subscription" link.
    2.  Open v2rayNG -> Menu -> Subscription Group Setup -> Add.
    3.  Paste link -> Update Subscription.
*   **NekoBox**: Best for Sing-box configs.
*   **Clash Meta**: Required for our Clash configs (standard Clash doesn't support VLESS).

### iOS
*   **Shadowrocket**: Paid, but best. Supports everything.
    *   Import using the "Shadowrocket" specific link for optimized tags.
*   **Streisand**: Good free alternative.
*   **Sing-box**: Official app available on TestFlight/AppStore.

### Windows / macOS
*   **v2rayN (Windows)**: The gold standard.
*   **Clash Verge (Windows/Mac)**: Modern Clash client.
*   **Sing-box (CLI/GUI)**: For advanced users.

## Advanced Usage

### How to use "The Sniper" (Router Mode)
The `singbox.json` output is designed as a "Sniper". It uses a `tun` interface but only routes traffic that matches specific rules (e.g., blocked domains).
1.  Download `singbox.json`.
2.  Run `sing-box run -c singbox.json`.
3.  Set your device gateway to the machine running Sing-box.

### How to use "The Tank" (VPN Mode)
The `singbox-vpn.json` is a "Tank". It routes **everything** through the proxy.
*   WARNING: This will route local traffic too if not configured correctly.
*   Use this when you are on a very hostile network (e.g., public WiFi) and want full encryption.

## Lab Scanner Troubleshooting

### "No clean IPs found"
*   Your ISP may be blocking all Cloudflare WARP ports. Try `--scan-ports` to see which ports are open.
*   Try adding your own IPs: `python tools/lab-scanner.py --scan-ips --custom-ips "1.2.3.4:2408"`.
*   Consider non-WARP strategies: `python tools/lab-scanner.py --auto-chain` tries 6 strategies including relay chain and proxy cascade.

### "No auto-chain path found"
The 6-strategy auto-chain failed. This means:
1.  No direct proxy access.
2.  No local proxies discovered (Psiphon, V2RayN, etc.).
3.  No LAN relays with internet access.
4.  No clean WARP IPs found.

**Solutions:**
*   Install a circumvention tool (Psiphon, Lantern, Tor) as Layer 1, then re-run `--auto-chain`.
*   Check if your network has a corporate proxy: `python tools/lab-scanner.py --scan-relays`.
*   Try the interactive builder: `python tools/lab-scanner.py --interactive` — manually add layers and test.

### "scan-lan finds hosts but none have internet"
*   The hosts are reachable on your LAN but cannot access the internet themselves.
*   Try different hosts or ports. Some corporate proxies require authentication.
*   Check if the proxy requires a username/password (the scanner tests unauthenticated access only).

### Lab Web Page: "No pipeline proxies available"
*   The `output/base64.txt` file may not be deployed yet, or CORS prevents fetching.
*   Paste your own proxy URI manually, or download `tools/lab-scanner.py` for offline scanning.

## Multi-Strategy Decision Guide

Not sure which strategy to use? Follow this flowchart:

1.  **Can you reach your proxy directly?** → Use **Direct** (no chain needed).
2.  **Can you reach Cloudflare IPs?** → Use **WARP** or **vwarp AtomicNoize** (TLS fragmentation; ConfigStream's built-in tls_fragment was removed by sing-box).
3.  **Do you have a local proxy (Psiphon/Lantern/V2Ray)?** → Use **Proxy Cascade**.
4.  **Is there any intermediate proxy with better access (LAN, remote, pipeline)?** → Use **Relay Chain**.
5.  **Can your local proxy reach Cloudflare?** → Use **Local Proxy + WARP**.
6.  **Nothing works directly?** → Use **LAN Relay + WARP** or deploy a **CDN Worker**.

Run `python tools/lab-scanner.py --auto-chain` to automatically test all 6 strategies.

## Pipeline & Infrastructure Issues

### "Go Binary Not Found"
If you see `WarpScannerWorker: Go binary not found`, the pipeline cannot find the compiled Go tester.
*   **Fix:** Compile it: `cd src/go/tester && go build -o configstream-tester .`
*   **CI:** Check `.github/workflows/main.yml` to ensure the `build_go` step ran successfully.

### "Washing Skipped: No WARP keys"
The `WARP_KEY_POOL` environment variable is empty or malformed.
*   **Fix:** Provide a valid JSON array of WARP credentials.
*   **Local Dev:** `export WARP_KEY_POOL='[{"id":"...", "private_key":"...", "peer_public_key":"..."}]'`

### "Address already in use" (Go Tester)
The Go tester binds to random ports (10000-60000) for local SOCKS listeners. In high-concurrency modes, collisions can occur.
*   **Fix:** Reduce `--max-workers` count or check if other services are occupying ports.

### "NameError: List" or Type Hint Errors
Indicates Python 3.8/3.9 without `from typing import List`.
*   **Fix:** Use Python 3.10+ (required by ConfigStream).

### Globe Not Loading
The 3D Globe requires WebGL.
*   **Fix:** Enable Hardware Acceleration in your browser. Check console for `three.js` errors.

### "No Data" in Analytics Charts
If analytics show zeros:
*   **Cause:** The pipeline may have failed before the `save_metadata` step.
*   **Check:** Inspect `output/metadata.json` — if it is empty or missing fields, the pipeline did not complete output generation.

### "Connection Refused" on Washed Proxies
If proxies tagged `GOLD-` or `🛡️ Secure` are not connecting:
*   **Cause:** The Cloudflare endpoint may be blocked in your region, or the WARP key quota is exhausted.
*   **Fix:** Try a different Clean IP or rotate WARP keys.

## Getting Help
If you encounter persistent issues, please open an issue on GitHub with:
1.  Your client name and version.
2.  The specific error message.
3.  Which subscription link you are using.
4.  If using the Lab Scanner, include the `lab-scan-results.json` output file.

## Related Documentation

*   **[Getting Started](getting_started.md)** — Installation, first run, Docker setup.
*   **[Configuration Reference](Configuration.md)** — All environment variables and their defaults.
*   **[Evasion Mode Guide](../../CENSORSHIP_EVASION.md)** — Choosing the right evasion mode for your censorship environment.
*   **[Sing-box Configuration Guide](../encyclopedia/tools/singbox_configuration_guide.md)** — Understanding the config files you're importing.
*   **[Firewalls & Honeypots](../encyclopedia/security/firewall_honeypot.md)** — Why certain protocols fail in certain countries.
*   **[WARP & Clean IPs](../encyclopedia/networking/warp.md)** — Troubleshooting washed/shielded proxy issues.
