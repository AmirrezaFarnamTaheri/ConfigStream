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

# Run unit tests and type checks
pytest tests/ -q
mypy src/configstream
```

## Docker Deployment

### Docker Compose (Recommended)

The `docker-compose.yml` defines two services:
1.  **web**: The FastAPI server (port 8000).
2.  **worker**: The background pipeline process.

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Scale workers (if supported by future arch)
docker compose up -d --scale worker=2
```

### PWA & HTTPS

To fully enable PWA features (Service Workers), the dashboard **must** be served over HTTPS.
-   **Development**: `localhost` is treated as a secure context.
-   **Production**: Use a reverse proxy (Nginx, Caddy, Traefik) with SSL termination in front of the Docker container.

Example Nginx config:
```nginx
server {
    listen 443 ssl;
    server_name configstream.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
*Note: The `Upgrade` headers are required for the WebSocket feed.*

## GitHub Actions CI/CD

Workflows live under `.github/workflows/`:

-   `pipeline.yml`: Scheduled runs (every 6 hours).
-   `deploy-pages.yml`: Publishes the `output/` directory to GitHub Pages.
-   `healthcheck.yml`: Validates pipeline results.

### Secrets

Configure these in your repository settings:
-   `MAXMIND_LICENSE_KEY`: Required for GeoIP updates.
-   `GH_TOKEN` (Optional): For pushing to other branches/repos.

## Scaling & Performance

### Resource Requirements
-   **Minimum**: 1 vCPU, 512MB RAM (for ~1000 proxies).
-   **Recommended**: 2 vCPU, 2GB RAM (for ~100k proxies).

### Optimization Tips
1.  **Database**: Ensure the SQLite database resides on a fast disk (NVMe).
2.  **Network**: The worker is network-bound. Use a server with high bandwidth and low latency.
3.  **Concurrency**: Tune `MAX_WORKERS` in `configstream/config.py` or via environment variable `MAX_WORKERS`. Default is conservative (50).

## Production Checklist

- [ ] **Security**: Change default API keys (if any).
- [ ] **SSL**: Enable HTTPS for PWA support.
- [ ] **Persistence**: Mount a volume for `data/` to persist intelligence databases (`source_quality.db`).
- [ ] **Monitoring**: Set up uptime monitoring for `/health` endpoint.
- [ ] **Updates**: Regularly pull the latest Docker image.

---

_Last updated: November 2025_
