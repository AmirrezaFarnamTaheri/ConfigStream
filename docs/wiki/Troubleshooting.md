# ConfigStream Troubleshooting Guide

## Common Issues

### 1. "Signature Verification Failed"
- **Symptom:** The frontend displays a security alert or refuses to load proxies.
- **Cause:** The `frontend/assets/js/constants.js` public key does not match the private key used by the CI pipeline to sign the subscription.
- **Fix:**
    - Rotate keys in GitHub Secrets.
    - Update `PUBLIC_KEY` in `constants.js` with the new public key.

### 2. "Proxy List Empty"
- **Symptom:** `proxies.json` is empty `[]`.
- **Cause:**
    - Fetcher failed to retrieve sources (network blocking or 404).
    - All proxies failed validation (strict mode enabled).
- **Fix:** Check CI logs for `fetch_from_source` errors. Verify `TEST_URLS` are reachable from the GitHub Actions runner.

### 3. "Steganography Image Corrupt"
- **Symptom:** `gallery.png` does not load or decoder fails.
- **Cause:** The CDN or image optimization service (e.g., Cloudflare Polish) stripped the appended Zip data.
- **Fix:** Ensure the file is served with `Cache-Control: no-transform`. Use raw storage (GitHub Releases, Discord) instead of image hosts.

### 4. IPFS Fallback Not Working
- **Symptom:** Primary domain is down, but IPFS doesn't load.
- **Cause:** IPNS propagation is slow (up to an hour).
- **Fix:** Use DNSLink (`_dnslink.fallback.com`) for instant updates. Check if the Pinata API token is valid in secrets.

## Debugging

### Enable Verbose Logging
Set `LOG_LEVEL=DEBUG` in your environment or `.env` file before running the pipeline.

```bash
export LOG_LEVEL=DEBUG
python -m configstream
```

### Manual Testing
Use the CLI to test a single proxy:
```bash
python -m configstream test --proxy "vless://..."
```
