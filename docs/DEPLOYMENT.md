# Deployment Guide

ConfigStream is designed for flexibility, supporting automated cloud environments (GitHub Actions), containerized setups (Docker), and traditional VPS deployments.

## 1. GitHub Actions (Recommended)

This is the standard zero-cost deployment method. The repository is pre-configured to run the pipeline on a schedule and publish results to GitHub Pages.

### Prerequisites
- A GitHub account.
- A fork of this repository.

### Setup Steps
1.  **Fork the Repository**: Click the "Fork" button on the top right of the GitHub page.
2.  **Enable Actions**: Go to the "Actions" tab in your forked repository and enable workflows if prompted.
3.  **Configure Pages**:
    -   Go to **Settings** > **Pages**.
    -   Under "Build and deployment", select **Deploy from a branch**.
    -   **Branch**: Select `gh-pages` (Note: This branch is created automatically after the first successful pipeline run. You may need to wait for the first run to complete).
    -   **Folder**: `/ (root)`.

### Configuration (Secrets & Variables)
You can customize the behavior using GitHub Repository Secrets/Variables:

-   `MAXMIND_LICENSE_KEY` (Secret): Optional. If provided, the pipeline downloads fresh GeoIP databases from MaxMind. Otherwise, it falls back to public mirrors.
-   `CF_API_TOKEN` (Secret): Optional. Required if you want to purge Cloudflare cache after deployment.

### Usage
The pipeline runs automatically:
-   **Schedule**: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC).
-   **Manual**: Go to Actions > "ConfigStream Pipeline" > "Run workflow".

---

## 2. Docker Deployment

Ideal for local development or running on a dedicated server/VPS with isolation.

### Prerequisites
-   Docker and Docker Compose installed.

### Setup
1.  Clone the repository:
    ```bash
    git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
    cd ConfigStream
    ```
2.  Build and Start:
    ```bash
    docker-compose up --build -d
    ```

### Services
-   **`worker`**: Runs the aggregation pipeline on a schedule (cron-like behavior inside the container).
-   **`web`**: A FastAPI/Nginx server hosting the `output/` directory and the web dashboard on port 8000.

### Access
-   Dashboard: `http://localhost:8000`
-   Subscription: `http://localhost:8000/files/base64.txt`

---

## 3. VPS / Dedicated Server (Manual)

For users who prefer bare-metal performance or custom scheduling.

### Requirements
-   Python 3.10+
-   `sing-box` binary installed and in system PATH.
-   Git

### Installation
1.  Install the package:
    ```bash
    pip install .
    ```
    *Or for development:* `pip install -e ".[dev]"`

2.  Verify installation:
    ```bash
    configstream --help
    ```

### Running the Pipeline
Execute the `merge` command:
```bash
configstream merge --sources sources/batch_1.txt --output /var/www/html/configstream
```

### Automation (Cron)
Add a crontab entry to run every 6 hours:
```bash
0 */6 * * * /usr/local/bin/configstream merge --sources /path/to/sources.txt --output /var/www/html/configstream >> /var/log/configstream.log 2>&1
```

---

## 4. CDN Integration (Cloudflare)

To serve configurations globally with low latency, putting a CDN in front of your deployment is highly recommended.

### For GitHub Pages
1.  Add your custom domain to the GitHub Pages settings.
2.  Configure your DNS in Cloudflare to proxy traffic (Orange Cloud) to GitHub.
3.  **Page Rules**: Create a rule for `*yourdomain.com/*.txt` and `*yourdomain.com/*.json` with settings:
    -   **Cache Level**: Cache Everything
    -   **Edge Cache TTL**: 2 hours

### For Docker/VPS
1.  Point your domain's A record to your server IP.
2.  Ensure port 80/443 is open.
3.  Use Nginx/Caddy as a reverse proxy in front of the ConfigStream web server/files.

---

## Troubleshooting

### "Database is locked"
-   **Cause**: Concurrent writes to the SQLite database.
-   **Solution**: The system now uses WAL mode to mitigate this. Ensure you are not running multiple pipeline instances simultaneously on the same `data/` directory.

### "GitHub Action failed to push"
-   **Cause**: `gh-pages` branch conflict or permissions.
-   **Solution**: Ensure "Read and Write permissions" are enabled in Settings > Actions > General > Workflow permissions.

### "Sing-box not found"
-   **Cause**: The `sing-box` binary is missing from the environment.
-   **Solution**: Ensure `sing-box` is installed. The Docker image and GitHub Action runner handle this automatically. On a VPS, download it from the official release page and place it in `/usr/local/bin`.
