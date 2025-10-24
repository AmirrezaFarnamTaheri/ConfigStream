# Deployment Guide

## Local Development

### Prerequisites
- Python 3.10+
- Git
- Poetry or pip
- (Optional) Docker 24+

### Installation

```bash
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
cd ConfigStream
python -m venv .venv
. .venv/Scripts/Activate.ps1  # PowerShell
pip install --upgrade pip
pip install -e ".[dev]"
```

### Useful Commands

```bash
# Run aggregation pipeline with defaults
configstream merge --sources sources.txt --output output/

# Retest previously generated proxies
configstream retest --input output/proxies.json --output output/

# Display inline metrics after a run
configstream merge --sources sources.txt --output output/ --show-metrics

# Produce a JSON performance report
python scripts/performance_report.py --sources sources.txt --max-proxies 50

# Run unit tests and type checks
pytest tests/ -q
mypy src/configstream
```

## Docker Deployment

### Sample Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY . .
RUN pip install --no-cache-dir -e "."

ENTRYPOINT ["configstream"]
CMD ["--help"]
```

### Build and Run

```bash
docker build -t configstream:latest .
docker run --rm -v $PWD/output:/app/output configstream merge \
  --sources sources.txt --output output/
```

Set `LOG_LEVEL=DEBUG` or `TEST_TIMEOUT=20` via `-e` flags to override defaults.

## GitHub Actions CI/CD

Workflows live under `.github/workflows/`:

- `pipeline.yml`: scheduled and manual runs of the merge pipeline
- `deploy-pages.yml`: publishes static dashboards to GitHub Pages
- `release.yml`: builds tagged releases

Recommended steps when forking:

1. Enable GitHub Pages (Settings → Pages → GitHub Actions).
2. Configure repository secrets if you use GeoIP (`MAXMIND_LICENSE_KEY`).
3. Review workflow schedules to align with your quota limits.

## Scheduled Retesting

Use `configstream.scheduler.RetestScheduler` to keep proxy results fresh.
The helper wraps `run_full_pipeline` and stores performance metrics for
each cycle.

```python
from datetime import timedelta
from configstream.scheduler import RetestScheduler

scheduler = RetestScheduler("output/proxies.json", interval=timedelta(hours=6))
scheduler.start()
```

Run the scheduler inside a long-lived process (systemd service, Docker
container, etc.) to continually refresh generated artifacts.

## Production Checklist

- [ ] `pytest tests/ -v`
- [ ] `mypy src/configstream`
- [ ] `flake8 src/configstream`
- [ ] `bash scripts/security_audit.sh`
- [ ] `python scripts/profile_performance.py`
- [ ] GeoIP databases downloaded (`data/GeoLite2-*.mmdb` present)
- [ ] Output directory write permissions verified
- [ ] Monitoring/alerting configured for workflow failures

## Troubleshooting

### Slow Pipeline Runs
- Reduce concurrency: `--max-workers 5`
- Limit proxies: `--max-proxies 100`
- Increase timeout cautiously: `--timeout 20`

### GeoIP Failures
- Ensure `MAXMIND_LICENSE_KEY` is exported
- Run `configstream geoip-download` (if command enabled)
- Verify network access from runner

### Empty Outputs
- Check `configstream.log` for fetch errors
- Validate sources manually via curl
- Confirm subscription files are not base64-encoded or empty

---

_Last updated: October 2025_
