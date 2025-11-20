# Contributing to ConfigStream

First off, thanks for taking the time to contribute! 🎉

ConfigStream is a community-driven project, and we value your input. Whether you're fixing a bug, improving documentation, or adding a new feature, your help is appreciated.

## How to Contribute

### 1. Reporting Bugs
If you find a bug, please open an issue on GitHub. Include:
-   Steps to reproduce.
-   Expected behavior vs. actual behavior.
-   Logs or screenshots if applicable.

### 2. Suggesting Features
Have an idea? Open a "Feature Request" issue. Describe the problem you're solving and your proposed solution.

### 3. Submitting Code

1.  **Fork the repository** and create your branch from `main`.
2.  **Install dependencies**:
    ```bash
    pip install -e ".[dev]"
    ```
3.  **Make your changes**. Ensure you follow the coding style (we use `black` and `flake8`).
4.  **Run tests**:
    ```bash
    pytest
    ```
5.  **Verify types**:
    ```bash
    mypy .
    ```
6.  **Commit your changes**. Please use descriptive commit messages.
7.  **Push to your fork** and submit a Pull Request.

## Roadmap & Next Steps 🗺️

We have an ambitious vision for ConfigStream. Below is a detailed breakdown of features, methods, and improvements we are actively working on or looking for help with.

### 🤖 AI & Automation
* **Reinforcement Learning Scheduler**:
  * **Goal**: Implement an RL agent (e.g., Q-Learning) to optimize retest intervals per proxy.
  * **Metrics**: Latency stability, uptime history, and bandwidth usage.
* **Predictive Anomaly Detection**:
  * **Goal**: Use time-series analysis (Prophet/ARIMA) to predict source failures before they happen.
* **Natural Language Source Discovery**:
  * **Goal**: Create a scraper that parses Telegram channels or forums using NLP to extract subscription links automatically.
* **Automated Protocol Fingerprinting**:
  * **Goal**: Use ML to identify the true protocol of an obfuscated stream, ignoring the advertised config header.

### 🌍 Localization & Access
* **Multi-Language Dashboard**:
  * **Goal**: Add i18n support to the frontend (Chinese, Persian, Russian, Arabic, Spanish, Indonesian).
* **Mirror & CDN Integration**:
  * **Goal**: Automate deployment to IPFS, Cloudflare Pages, or Vercel for censorship-resistant distribution.
* **Telegram Bot Integration**:
  * **Goal**: Build a bot that users can query for fresh proxies directly or subscribe to updates.
* **Tor Onion Service**:
  * **Goal**: Deploy the dashboard as a Hidden Service for maximum accessibility in restrictive environments.

### 🛠️ Infrastructure & DevOps
* **Distributed Workers (Celery/Redis)**:
  * **Goal**: Scale the pipeline across multiple nodes for massive-scale crawling.
* **Database Migration (PostgreSQL)**:
  * **Goal**: Migrate from SQLite to PostgreSQL to support concurrent write operations and larger datasets.
* **Docker Swarm / K8s Support**:
  * **Goal**: Create Helm charts for deploying ConfigStream clusters.
* **Observability Stack**:
  * **Goal**: Integrate Prometheus/Grafana for real-time metrics on pipeline health and node performance.

### 🛡️ Advanced Security
* **TLS Fingerprint Randomization**:
  * **Goal**: Randomize uTLS fingerprints during testing to avoid active probing detection.
* **Deep Packet Inspection (DPI) Evasion**:
  * **Goal**: Implement fragmentation strategies in the tester to verify DPI bypass capabilities.
* **Malware Scanning**:
  * **Goal**: Integrate with VirusTotal API to scan domains/IPs against known malware databases.
* **JARM Fingerprinting**:
  * **Goal**: Fingerprint the remote servers to detect standard V2Ray/Trojan deployments vs honeypots.

### 🔌 Protocol Expansion
* **V2Ray REALITY Verification**:
  * **Goal**: Add specific checks for REALITY protocol constraints (SNI mismatch, stealing).
* **OpenVPN Support**:
  * **Goal**: Add parsing and testing for standard OpenVPN profiles (.ovpn).
* **SSTP / L2TP / IKEv2**:
  * **Goal**: Support legacy enterprise VPN protocols for broader compatibility.
* **Shadowsocks-Rust Integration**:
  * **Goal**: Use the official Rust core via FFI for higher performance testing.

### 📊 Data Science & Analytics
* **Churn Prediction**:
  * **Goal**: Analyze how long proxies survive on average based on provider/ASN.
* **Network Topology Mapping**:
  * **Goal**: Visualize the physical location of proxies vs. their claimed location (latency triangulation).
* **Provider Reliability Index**:
  * **Goal**: Rank ISPs and hosting providers by their tendency to host reliable vs short-lived proxies.

### 💻 Frontend & UX
* **Dark/Light Mode Toggle**:
  * **Goal**: Respect system preferences but allow manual override (already partially implemented, needs refinement).
* **Accessibility (a11y)**:
  * **Goal**: Ensure the dashboard meets WCAG 2.1 AA standards for screen readers.
* **QR Code Sharing**:
  * **Goal**: Generate QR codes for individual proxies or subscriptions directly in the UI.

### 🧑‍💻 Developer Experience
* **Pre-commit Hooks**:
  * **Goal**: Expand hooks to include security scanning (`gitleaks`, `bandit`).
* **Dev Containers**:
  * **Goal**: Add `.devcontainer` configuration for one-click VS Code setup.
* **API Documentation**:
  * **Goal**: Generate OpenAPI/Swagger docs for the backend API endpoints.

## Development Guidelines

-   **No Placeholders**: Avoid `TODO` or incomplete code in the `main` branch.
-   **Testing**: Add unit tests for new logic. Use `hypothesis` for fuzz testing parsers.
-   **Security**: Do not commit API keys or secrets. Use environment variables.
-   **Documentation**: Update `README.md` or `ARCHITECTURE.md` if you change core functionality.

## Project Structure

-   `src/configstream/`: Core Python source code.
-   `frontend/`: Web dashboard assets (HTML/CSS/JS).
-   `tests/`: Unit and integration tests.
-   `sources/`: Text files containing proxy source URLs.

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0 License.
