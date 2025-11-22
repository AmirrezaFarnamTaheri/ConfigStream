# Troubleshooting Guide

This guide covers common issues encountered when running, developing, or deploying ConfigStream.

## General Issues

### Pipeline Fails with "Out of Memory" (OOM)
**Symptoms:** GitHub Action crashes with exit code 137 or similar.
**Cause:** The fetcher is downloading too much data into memory, or `sing-box` is testing too many proxies at once.
**Solution:**
1. **Limit Source Size:** Ensure sources are split into batches (handled by `fetch_multiple_sources` 50MB limit).
2. **Reduce Concurrency:** Lower `MAX_WORKERS` or `PER_HOST_MAX_CONCURRENCY` in `src/configstream/config.py`.
3. **Use Adaptive Workers:** The pipeline automatically calculates workers based on CPU/RAM. Ensure `max_workers=0` (auto) is used.

### "Database is locked" Errors
**Symptoms:** `sqlite3.OperationalError: database is locked` in logs.
**Cause:** Multiple concurrent writers to `anomaly.db` or `source_quality.db`.
**Solution:**
1. **WAL Mode:** Ensure WAL mode is enabled (FIXED in v1.2.0).
2. **Timeout:** Increase SQLite timeout in connection string (default is 30s).
3. **Single Writer:** Ensure only one pipeline instance runs per database file, or use the merging strategy (`scripts/merge_batches.py`).

### "No proxies found" / Empty Output
**Symptoms:** Pipeline runs successfully but generates 0 proxies.
**Cause:**
1. **All sources failed:** Check logs for "Fetch failed" or "Blocked source".
2. **Strict Parsing:** Parsers rejected malformed configs. Check debug logs.
3. **Strict Testing:** All proxies failed the latency/connectivity test.
4. **GeoIP Failure:** Proxies worked but GeoIP failed to resolve country, and strict country filter was on.
**Solution:**
1. Run with `--leniency` flag to skip strict checks.
2. Check `data/source_quality.db` to see if sources are on cooldown.

## Development Issues

### Tests Failing locally
**Symptoms:** `pytest` fails with `RuntimeError: Event loop is closed` or similar.
**Cause:** Asyncio loop management conflict between `pytest-asyncio` and `playwright`.
**Solution:**
1. Ensure `nest_asyncio.apply()` is called in `conftest.py`.
2. Use `python -m pytest` instead of just `pytest`.

### Frontend Assets Not Loading
**Symptoms:** 404 errors for `.js` or `.css` files.
**Cause:** Incorrect path resolution in `utils.js`.
**Solution:**
1. Ensure you are accessing via the correct URL (root vs `/files/`).
2. Check `frontend/assets/js/utils.js` fallback logic.

## Deployment Issues

### GitHub Pages 404 on `metadata.json`
**Symptoms:** Frontend loads but shows "No Data". Console shows 404 for `metadata.json`.
**Cause:** The deployment job didn't copy `output/` files to the root of `gh-pages` branch properly.
**Solution:**
1. Check the `deploy` step in `.github/workflows/pipeline.yml`.
2. Verify the artifact structure.

### Telegram Bot Not Responding
**Symptoms:** Bot is silent.
**Cause:** Webhook not set or Worker failed.
**Solution:**
1. Check Cloudflare Worker logs.
2. Re-register webhook: `https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WORKER_URL>`
