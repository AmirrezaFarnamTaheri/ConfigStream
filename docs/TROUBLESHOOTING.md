# ConfigStream Troubleshooting Guide

Common issues and solutions for ConfigStream deployment and operation.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Pipeline Errors](#pipeline-errors)
3. [Testing Problems](#testing-problems)
4. [Output Generation Issues](#output-generation-issues)
5. [Performance Problems](#performance-problems)
6. [Database Issues](#database-issues)
7. [Frontend Issues](#frontend-issues)
8. [CI/CD Problems](#cicd-problems)

---

## Installation Issues

### Problem: `pip install -e .` fails with dependency conflicts

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
```

**Solutions:**
1. Use a fresh virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -e .[dev]
```

2. If using Python 3.12+, some dependencies may not yet have wheel builds. Use Python 3.11:
```bash
pyenv install 3.11
pyenv local 3.11
```

---

### Problem: `ModuleNotFoundError: No module named 'singbox2proxy'`

**Symptoms:**
```
ImportError: cannot import name 'SingBoxProxy' from 'singbox2proxy'
```

**Solutions:**
1. Ensure all dependencies are installed:
```bash
pip install singbox2proxy~=0.2.4
```

2. If package not found, check PyPI availability or install from source:
```bash
git clone https://github.com/username/singbox2proxy.git
cd singbox2proxy
pip install .
```

---

## Pipeline Errors

### Problem: "Database is locked" errors in SQLite

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Solutions:**
1. **Fixed in v1.2.0+**: WAL mode is now enabled by default
2. If using older version, manually enable:
```python
conn.execute("PRAGMA journal_mode=WAL")
```

3. Reduce concurrency if still happening:
```bash
configstream merge --sources sources.txt --max-workers 5
```

---

### Problem: Fetch timeouts for all sources

**Symptoms:**
```
⚠️ Fetch Summary: 0/668 sources successful
Max retries exceeded: TimeoutError
```

**Solutions:**
1. Check internet connection
2. Check if behind firewall/proxy
3. Increase timeout:
```bash
configstream merge --sources sources.txt --timeout 30
```

4. Check if sources.txt has valid URLs:
```bash
head -5 sources/batch_1.txt
```

---

### Problem: Anomaly detector blocks all sources

**Symptoms:**
```
⚠️ BLOCKING https://example.com: Isolation Forest Outlier (Count: 5432)
```

**Solutions:**
1. This is expected behavior if a source suddenly returns 2x normal count (possible poisoning)
2. To reset anomaly history:
```bash
rm data/anomaly.db
```

3. To disable anomaly detection (NOT recommended for production):
   - Comment out anomaly check in `pipeline.py:200-219`

---

##  Testing Problems

### Problem: All proxies fail tests

**Symptoms:**
```
Testing... (0 working)
Final count: 0
```

**Solutions:**
1. Check if sing-box is installed:
```bash
which sing-box
sing-box version
```

2. Install sing-box if missing:
```bash
# Linux
curl -L https://github.com/SagerNet/sing-box/releases/latest/download/sing-box-linux-amd64.tar.gz -o sing-box.tar.gz
tar -xzf sing-box.tar.gz
sudo mv sing-box*/sing-box /usr/local/bin/

# macOS
brew install sing-box
```

3. Test manually with a known working proxy:
```bash
python -c "
from configstream.testers import SingBoxTester
from configstream.models import Proxy
p = Proxy(config='vmess://...', protocol='vmess', address='example.com', port=443)
tester = SingBoxTester()
import asyncio
result = asyncio.run(tester.test(p))
print(f'Working: {result.is_working}, Latency: {result.latency}')
"
```

---

### Problem: Tests are very slow

**Symptoms:**
```
Testing 1000 proxies takes > 30 minutes
```

**Solutions:**
1. Increase workers (default is auto-detected):
```bash
configstream merge --sources sources.txt --max-workers 20
```

2. Enable test caching (automatically used if available):
```bash
# Cache persists in data/test_cache.json
ls -lh data/test_cache.json
```

3. Use adaptive timeout (enabled by default in v1.2.0+)

---

## Output Generation Issues

### Problem: `proxies.json` is empty or corrupt

**Symptoms:**
```json
[]
```
or
```
Unexpected end of JSON input
```

**Solutions:**
1. Check pipeline logs for errors:
```bash
configstream merge --sources sources.txt 2>&1 | tee pipeline.log
grep ERROR pipeline.log
```

2. Check disk space:
```bash
df -h .
```

3. **Fixed in v1.2.0+**: Output files now use fsync for crash safety

---

### Problem: Clash/Sing-box config doesn't work in client

**Symptoms:**
- Clash: "All proxies failed"
- Sing-box: "Connection refused"

**Solutions:**
1. Validate YAML/JSON syntax:
```bash
# Clash
python -c "import yaml; yaml.safe_load(open('output/clash.yaml'))"

# Sing-box
python -c "import json; json.load(open('output/singbox.json'))"
```

2. Test with single proxy first:
   - Extract one proxy from output
   - Test manually in client
   - Check if issue is with specific proxy or entire config

3. Check client compatibility (some clients don't support all protocols)

---

## Performance Problems

### Problem: Pipeline runs out of memory

**Symptoms:**
```
MemoryError
Killed
```

**Solutions:**
1. Limit max proxies to test:
```bash
configstream merge --sources sources.txt --max-proxies 5000
```

2. Process sources in batches:
```bash
for batch in sources/batch_*.txt; do
  configstream merge --sources $batch --output output_batch_${batch##*_}
done
```

3. Reduce workers:
```bash
configstream merge --sources sources.txt --max-workers 5
```

---

### Problem: High CPU usage during testing

**Symptoms:**
```
CPU: 100% for extended periods
```

**Solutions:**
1. This is expected - concurrent testing is CPU-intensive
2. Limit workers to reduce CPU:
```bash
configstream merge --sources sources.txt --max-workers 10
```

3. Use nice/ionice to reduce priority:
```bash
nice -n 19 ionice -c 3 configstream merge ...
```

---

## Database Issues

### Problem: "database disk image is malformed"

**Symptoms:**
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solutions:**
1. Recover from backup (if available):
```bash
ls data/backups/
cp data/backups/source_quality_20251121.db data/source_quality.db
```

2. Reset databases (loses history):
```bash
rm data/*.db
# Pipeline will recreate on next run
```

3. **Prevention (v1.2.0+)**: WAL mode + fsync prevent corruption

---

### Problem: Database backup files growing too large

**Symptoms:**
```
data/backups/ is 500MB+
```

**Solutions:**
1. Reduce retention period:
```bash
configstream backup --retention-days 3
```

2. Manual cleanup:
```bash
find data/backups -name "*.db" -mtime +7 -delete
```

---

## Frontend Issues

### Problem: Dashboard shows "No data available"

**Symptoms:**
- Frontend loads but shows zeros
- Console error: "Failed to fetch metadata.json"

**Solutions:**
1. Check if output files exist:
```bash
ls -lh output/metadata.json output/proxies.json
```

2. Check file paths in frontend match backend output:
   - Frontend expects: `output/metadata.json`
   - Backend generates: `output_dir/metadata.json`

3. Serve from correct directory:
```bash
cd frontend
python -m http.server 8000
# Open http://localhost:8000
```

---

### Problem: PWA not installing

**Symptoms:**
- No "Install App" prompt in browser
- Service worker errors

**Solutions:**
1. PWA requires HTTPS (except localhost):
   - Use ngrok: `ngrok http 8000`
   - Or deploy to GitHub Pages

2. Check manifest.json:
```bash
cat frontend/manifest.json
```

3. Check service worker registration:
   - Open DevTools → Application → Service Workers
   - Look for errors

---

## CI/CD Problems

### Problem: GitHub Actions workflow fails on "pipeline" job

**Symptoms:**
```
Error: Process completed with exit code 1
```

**Solutions:**
1. Check workflow logs:
   - Go to Actions tab → Click failed run → Expand logs

2. Common causes:
   - **Network issues**: Sources unreachable from GitHub servers
   - **Memory limits**: Reduce `--max-workers` in pipeline.yml
   - **Timeout**: Increase job timeout in pipeline.yml

3. Test locally first:
```bash
configstream merge --sources sources/batch_1.txt --output output_batch_1
```

---

### Problem: "Permission denied" when committing results

**Symptoms:**
```
error: failed to push some refs
Permission denied (publickey)
```

**Solutions:**
1. Check `GITHUB_TOKEN` permissions in workflow:
```yaml
permissions:
  contents: write
```

2. Ensure branch protection doesn't block bot commits

---

## Getting Help

### Before Opening an Issue

1. **Check logs**:
```bash
configstream merge --sources sources.txt 2>&1 | tee debug.log
```

2. **Check versions**:
```bash
python --version
pip show configstream
pip show singbox2proxy
```

3. **Minimal reproducible example**:
```bash
# Create minimal test case
echo "vmess://eyJh..." > test_source.txt
configstream merge --sources test_source.txt --output test_output/
```

### Opening an Issue

Include:
1. ConfigStream version
2. Python version
3. Operating system
4. Full error traceback
5. Minimal reproduction steps
6. Expected vs actual behavior

**GitHub Issues**: https://github.com/AmirrezaFarnamTaheri/ConfigStream/issues

---

## Advanced Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Pipeline State

```python
from configstream.pipeline import run_full_pipeline
from configstream.config import AppSettings

# Add breakpoint
import pdb; pdb.set_trace()

# Or use rich for pretty printing
from rich import print as rprint
rprint(stats)
```

### Profile Performance

```bash
python -m cProfile -o profile.stats -m configstream.cli merge --sources sources.txt
python -m pstats profile.stats
# (pstats) sort cumtime
# (pstats) stats 20
```

---

**Last Updated:** 2025-11-21
**Version:** 1.2.0
