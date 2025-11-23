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

## Getting Help
If you encounter persistent issues, please open an issue on GitHub with:
1.  Your client name and version.
2.  The specific error message.
3.  Which subscription link you are using.
