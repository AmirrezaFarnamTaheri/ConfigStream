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
    -   Under "Build and deployment", select **GitHub Actions**.
    -   The `deploy-pages.yml` workflow automatically deploys after a successful pipeline run.
4.  **Configure the release signing secret**:
    -   Go to **Settings** > **Secrets and variables** > **Actions** > **New repository secret**.
    -   Create `CS_SIGNING_PRIVATE_KEY_HEX` with the Ed25519 private signing key used for canonical release artifacts.
    -   The workflow may safely pass this repository secret into a job environment for the signing/preflight step, but do not store the private key in GitHub Actions Variables and never expose its value in logs, artifacts, issue text, or committed files.
    -   `CS_PUBLIC_KEY` is optional when `CS_SIGNING_PRIVATE_KEY_HEX` is present because the workflow can derive the matching public verification key. If you configure `CS_PUBLIC_KEY` explicitly, it must be a valid Ed25519 public key and must match the public key derived from the private signing key.

The scheduled `Config's Stream` workflow is fail-closed: production work and publication are intentionally blocked when the signing key is absent or malformed, when an explicitly configured public key is malformed, or when the public and private keys do not match. This prevents an unsigned or unverifiable artifact from becoming canonical. After provisioning or rotating the signing key, run `Config's Stream` manually once to verify release preflight before relying on the next scheduled publication.

### Configuration (Secrets & Variables)
You can customize the behavior using GitHub Repository Secrets/Variables:

-   `CS_SIGNING_PRIVATE_KEY_HEX` (Secret): **Required for scheduled/main publication.** Ed25519 private signing key used to sign canonical release artifacts. Keep the private material in a GitHub Actions Secret, not an Actions Variable.
-   `CS_PUBLIC_KEY` (Secret or variable): Optional explicit Ed25519 verification key. When omitted, it is derived from `CS_SIGNING_PRIVATE_KEY_HEX`; when provided, it must be valid and match the derived public key.
-   `WARP_KEY_POOL` (Secret): JSON array of Cloudflare WARP keys for proxy washing/revival. Example: `["key1","key2"]`. Without this, washing and revival features are disabled.
-   `VT_API_KEY` (Secret): Optional. VirusTotal API key for threat intelligence lookups.
-   `MAXMIND_LICENSE_KEY` (Secret): Optional. For fresh GeoIP databases from MaxMind.
-   `CF_API_TOKEN` (Secret): Optional. For Cloudflare cache purging after deployment.

#### Environment Variables (set in workflow or `.env`)
-   `VWARP_VERSION`: Vwarp binary version (default: `v2.2.2`).
-   `EVASION_MODE`: Evasion feature level — `aggressive`, `stealth`, or `standard`.
-   `FAIL_ON_ZERO_WORKING`: Set to `false` to allow pipeline to continue with 0 working proxies.

### Usage
The pipeline runs automatically:
-   **Schedule**: Automated via cron (see `main.yml` for current schedule).
-   **Manual**: Go to Actions > "Config's Stream" > "Run workflow".

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
-   Subscription: `http://localhost:8000/base64.txt`
-   Sing-box config: `http://localhost:8000/singbox.json`
-   Clash config: `http://localhost:8000/clash.yaml`

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
Add a crontab entry to run every 4 hours:
```bash
0 */4 * * * /usr/local/bin/configstream merge --sources /path/to/sources.txt --output /var/www/html/configstream >> /var/log/configstream.log 2>&1
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

### "Release prerequisite validation failed"
-   **Cause**: `CS_SIGNING_PRIVATE_KEY_HEX` is absent or malformed, `CS_PUBLIC_KEY` is malformed, or an explicitly configured public key does not match the private signing key.
-   **Solution**: Configure `CS_SIGNING_PRIVATE_KEY_HEX` as a GitHub Actions repository secret. If `CS_PUBLIC_KEY` is invalid or mismatched, remove it to allow automatic derivation from the private key, or replace it with the matching valid public key. Do not bypass this check or place private key material in a GitHub Actions Variable.

### "Database is locked"
-   **Cause**: Concurrent writes to the SQLite database.
-   **Solution**: The system now uses WAL mode to mitigate this. Ensure you are not running multiple pipeline instances simultaneously on the same `data/` directory.

### "GitHub Action failed to deploy"
-   **Cause**: Pages deployment artifact upload failed or permissions issue.
-   **Solution**: Ensure "Read and Write permissions" are enabled in Settings > Actions > General > Workflow permissions. Also verify that Pages is set to deploy from "GitHub Actions" (not a branch) in Settings > Pages.

### "Sing-box not found"
-   **Cause**: The `sing-box` binary is missing from the environment.
-   **Solution**: Ensure `sing-box` is installed. The Docker image and GitHub Action runner handle this automatically. On a VPS, download it from the official release page and place it in `/usr/local/bin`.

