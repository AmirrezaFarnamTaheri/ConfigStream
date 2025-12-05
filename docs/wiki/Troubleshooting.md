# Troubleshooting Guide

ConfigStream v2.0 introduces new components like the Go Scanner and Proxy Washer. This guide helps you diagnose common issues.

## 1. Pipeline Failures

### `Go Binary Not Found`
If you see `WarpScannerWorker: Go binary not found`, the pipeline cannot find the compiled Go tester.
*   **Fix:** Ensure you have compiled the binary: `cd src/go/tester && go build -o configstream-tester .`
*   **CI:** Check `.github/workflows/pipeline.yml` to ensure the `build_go` step is running correctly.

### `Washing Skipped: No WARP keys`
This means the environment variable `WARP_KEY_POOL` is empty or malformed.
*   **Fix:** Generate keys using the CLI or providing your own.
*   **Local Dev:** `export WARP_KEY_POOL='[{"id":"...", "private_key":"...", "peer_public_key":"..."}]'`

## 2. Testing Issues

### `Address already in use` (Go Tester)
The Go tester binds to random ports (10000-60000) for local SOCKS listeners. In high-concurrency modes, collisions might occur.
*   **Fix:** Reduce `--workers` count or check if other services are hogging ports.

### `NameError: List`
This usually indicates an issue with type hint imports in Python 3.8/3.9 environments without `from typing import List`.
*   **Fix:** Ensure you are using Python 3.10+ or correct the imports.

## 3. Frontend & Analytics

### Globe Not Loading
The 3D Globe uses WebGL.
*   **Fix:** Enable Hardware Acceleration in your browser. Check console for `three.js` errors.

### "No Data" in Charts
If analytics show zeros:
*   **Cause:** The pipeline might have failed before the `save_metadata` step.
*   **Check:** Look at `output/metadata.json` to see if it's empty or missing fields.

## 4. Connectivity

### "Connection Refused" on Washed Proxies
If proxies tagged `🛡️ Secure` are not connecting:
*   **Cause:** The Cloudflare endpoint might be blocked in your region, or the WARP key quota is exhausted.
*   **Fix:** Try a different `clean_ip` or rotate WARP keys.
