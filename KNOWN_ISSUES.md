# Known Issues and Limitations

## Recently Resolved (v3.0.2)
- **Remote frontend/CDN runtime dependencies**: Primary pages now load critical JS/CSS/fonts/globe/flag assets and Lab helper downloads from same-origin files, with static and browser smoke tests guarding against CDN regressions.
- **Xray WireGuard export**: Lab was incorrectly claiming Xray doesn't support WireGuard. Fixed — now generates native `secretKey` + `peers[]` format.
- **Clash/Xray transport**: Lab exports were missing WebSocket, gRPC, HTTP/2, httpupgrade, and Reality settings. Fixed with full transport support.
- **Trojan transport in Clash**: Pipeline Clash converter was missing ws/grpc transport for Trojan. Fixed.
- **WireGuard MTU default**: All converters now default to `mtu: 1280` for WireGuard outbounds.
- **Chain export scope**: Surge/Loon adapters only exported chains tagged `🛡️ Secure`. Now exports all WireGuard chains with `detour`.
- **Revived proxies in subscriptions**: `base64.txt` and `proxies.txt` now include revived proxy URIs.

For full resolved history, see `CHANGELOG.md`.

---

## 1. WASM Browser Networking Boundary

**Status:** Documented and guarded in v3.0.2

Browsers cannot open raw TCP/UDP sockets or perform native proxy handshakes from
WASM. The frontend WASM module (`src/go/tester/wasm_main.go`) uses
`syscall/js` and the browser `WebSocket` API only for browser-limited reachability checks on compatible WebSocket endpoints. Unsupported schemes and
invalid URLs are reported as browser-check failures while existing Go
sidecar/Python test results remain authoritative.

## 2. Mobile Layout Considerations

**Status:** Minor - Already Mitigated

The CSS includes comprehensive mobile responsive design with:
- `overflow-x: hidden` on all container elements
- Proper z-index hierarchy for mobile navigation
- Responsive grid layouts that adapt to screen size
- Touch-friendly target sizes

**Note:** The z-index mobile menu issue reported in early analysis has been **fixed** (header: 1000, nav-panel: 1005).

---

## 3. Country Flag Asset Dependency

**Status:** Resolved

Country rendering no longer depends on `flagcdn.com`. The proxy table uses vendored 20px flag PNGs with a text fallback only when an unknown or missing country asset is encountered.

---

## 4. Vwarp and Chain Statistics Display

**Status:** Fixed in Latest Commit

Previously, `smart_chain_count` and `vwarp_win_rate` were tracked in the backend but not displayed in the frontend.

**Resolution:** Added two new statistics cards to the dashboard:
- **Smart Chains:** Displays the count of topology-aware chains created
- **Vwarp Efficiency:** Shows the win rate percentage for WARP washing attempts

These statistics are now visible on the main dashboard and update with each pipeline cycle.

---

## 5. MIME Type Handling for WASM

**Status:** Fixed

Browsers require `.wasm` files to be served with `Content-Type: application/wasm`. This has been explicitly configured in `server.py`:

```python
mimetypes.add_type("application/wasm", ".wasm")
```

This ensures the FastAPI static file server serves WASM files with the correct MIME type.

---

## Contributing

If you can help address any of these issues, please submit a pull request or open an issue for discussion.
