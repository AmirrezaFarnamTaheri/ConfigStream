# Deployment Guide

ConfigStream is designed for flexibility, supporting automated cloud environments (GitHub Actions), containerized setups (Docker), and traditional VPS deployments.

## 1. GitHub Actions (Recommended)

This is the standard zero-cost deployment method. The repository is pre-configured to run the pipeline on a schedule and publish qualified results to GitHub Pages.

### Prerequisites
- A GitHub account.
- A fork of this repository.

### Setup Steps
1.  **Fork the Repository**: Click the "Fork" button on the top right of the GitHub page.
2.  **Enable Actions**: Go to the "Actions" tab in your forked repository and enable workflows if prompted.
3.  **Configure Pages**:
    -   Go to **Settings** > **Pages**.
    -   Under "Build and deployment", select **GitHub Actions**.
    -   The `deploy-pages.yml` workflow evaluates successful canonical pipeline artifacts and deploys only artifacts that satisfy the Pages trust policy and rollback requirements.
4.  **Configure the Pages trust policy**:
    -   **Recommended — signed publication**: create the repository secrets `CS_SIGNING_PRIVATE_KEY_HEX` and `CS_PUBLIC_KEY`. The private key signs release artifacts; the matching public key is an independent deployment trust anchor used to verify the candidate, the last-known-good snapshot, the deployed candidate, and any restored rollback release. `CS_PUBLIC_KEY` must match the private key.
    -   Store the private signing key only as a GitHub Actions **Secret**. Never put it in an Actions Variable, logs, artifacts, issue text, or committed files.
    -   **Explicit unsigned publication**: if you intentionally operate without signing material, remove both signing-related secrets and create the repository **Variable** `ALLOW_UNSIGNED_PAGES=true`. Unsigned Pages publication is disabled by default when this variable is absent or false.
    -   `ALLOW_UNSIGNED_PAGES=true` is not a signature bypass: if an artifact contains a manifest signature but `CS_PUBLIC_KEY` is missing or invalid, deployment is rejected rather than silently treating the artifact as unsigned.
    -   The same explicit unsigned policy now applies to rollback snapshots. An unsigned release can become the last-known-good baseline only when `ALLOW_UNSIGNED_PAGES=true`; a signed release still requires `CS_PUBLIC_KEY` and can never be downgraded to unsigned treatment.
    -   On the first deployment only, the workflow may bootstrap without a rollback baseline when its hardened snapshot probe proves that the trusted Pages origin returns HTTP 404 specifically for `artifact_manifest.json`. Other snapshot failures remain blocking. The manual `allow_bootstrap_without_lkg` input remains available for an explicit operator override.

The scheduled `Config's Stream` workflow can still generate an unsigned canonical artifact when no signing key is configured, but GitHub Pages publication is a separate trust boundary. A fork with neither valid signing configuration nor the explicit `ALLOW_UNSIGNED_PAGES=true` variable will fail closed before Pages mutation. If signing material is supplied, malformed keys, a public key without the matching signing key, or a public/private mismatch block publication.

### Configuration (Secrets & Variables)
You can customize the behavior using GitHub Repository Secrets/Variables:

-   `CS_SIGNING_PRIVATE_KEY_HEX` (Secret): Optional at artifact-generation time. When present, ConfigStream signs canonical release artifacts with Ed25519. For signed GitHub Pages publication, configure this together with the matching `CS_PUBLIC_KEY` secret.
-   `CS_PUBLIC_KEY` (Secret): Required trust anchor for signed GitHub Pages publication. It must be a valid Ed25519 public key and must match `CS_SIGNING_PRIVATE_KEY_HEX`. The main pipeline can derive a browser verification key from the private key, but the Pages deployment intentionally uses this independently configured public key to authenticate the release it receives.
-   `ALLOW_UNSIGNED_PAGES` (Repository Variable): Defaults to false when absent. Set exactly to `true` only when you intentionally want Pages to publish genuinely unsigned artifacts. It never authorizes a signed artifact whose trust key is missing.
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
-   **Cause**: Signing material was supplied but is inconsistent or malformed: for example an invalid `CS_SIGNING_PRIVATE_KEY_HEX`, an invalid `CS_PUBLIC_KEY`, `CS_PUBLIC_KEY` without a private signing key, or a public/private mismatch.
-   **Solution**: For signed publication, configure both a valid `CS_SIGNING_PRIVATE_KEY_HEX` secret and its exact matching `CS_PUBLIC_KEY` secret. For intentionally unsigned artifact generation, remove both signing-related values. Pages additionally requires the explicit repository variable `ALLOW_UNSIGNED_PAGES=true` before it will publish an unsigned artifact. Never place private key material in a GitHub Actions Variable.

### "Pages signature policy rejected the artifact"
-   **Cause**: Pages received an unsigned artifact while unsigned publication was not explicitly enabled, a signed artifact without `CS_PUBLIC_KEY`, or malformed/mismatched public-key material.
-   **Solution**: Prefer signed publication by configuring matching `CS_SIGNING_PRIVATE_KEY_HEX` and `CS_PUBLIC_KEY` secrets. If unsigned Pages publication is deliberate, ensure the artifact is genuinely unsigned and set the repository Variable `ALLOW_UNSIGNED_PAGES=true`. Do not use the variable to work around a signed-artifact verification failure.

### "Database is locked"
-   **Cause**: Concurrent writes to the SQLite database.
-   **Solution**: The system now uses WAL mode to mitigate this. Ensure you are not running multiple pipeline instances simultaneously on the same `data/` directory.

### "GitHub Action failed to deploy"
-   **Cause**: Pages deployment artifact upload failed, the artifact did not satisfy the trust/rollback policy, the first-deployment probe failed for a reason other than a missing `artifact_manifest.json`, or repository permissions are insufficient.
-   **Solution**: Inspect the `Qualify Pages Deployment Candidate` and `Locate, Verify, and Deploy Sealed Artifact` jobs first. Then verify Pages is configured for **GitHub Actions**, the required signing or explicit unsigned policy is configured, and the workflow has the repository permissions declared in `deploy-pages.yml`.

### "Sing-box not found"
-   **Cause**: The `sing-box` binary is missing from the environment.
-   **Solution**: Ensure `sing-box` is installed. The Docker image and GitHub Action runner handle this automatically. On a VPS, download it from the official release page and place it in `/usr/local/bin`.

