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

### 4. End-to-End Testing
If you make changes to the frontend, you must verify them visually.

1.  **Run the server locally**: `python -m http.server -d frontend 8000`
2.  **Check the UI**: Navigate to `http://localhost:8000` and `http://localhost:8000/analytics.html`.
3.  **Run E2E Tests**:
    ```bash
    pytest tests/e2e/
    ```

## Roadmap & Next Steps 🗺️

We have an ambitious vision for ConfigStream. Below is a detailed breakdown of features, methods, and improvements we are actively working on or looking for help with.

### 🤖 AI & Automation
* **Reinforcement Learning Scheduler**: Implement an RL agent (e.g., Q-Learning) to optimize retest intervals per proxy.
* **Predictive Anomaly Detection**: Use time-series analysis (Prophet/ARIMA) to predict source failures.
* **Automated Protocol Fingerprinting**: Use ML to identify the true protocol of an obfuscated stream.

### 🌍 Localization & Access
* **Multi-Language Dashboard**: Add i18n support to the frontend.
* **Mirror & CDN Integration**: Automate deployment to IPFS, Cloudflare Pages, or Vercel.
* **Telegram Bot Integration**: Build a bot for direct queries.

### 🛠️ Infrastructure & DevOps
* **Distributed Workers**: Scale the pipeline across multiple nodes.
* **Database Migration**: Migrate from SQLite to PostgreSQL for larger datasets.
* **Observability Stack**: Integrate Prometheus/Grafana.

### 🛡️ Advanced Security
* **TLS Fingerprint Randomization**: Randomize uTLS fingerprints during testing.
* **DPI Evasion**: Implement fragmentation strategies.
* **Malware Scanning**: Integrate with VirusTotal.

### 🔌 Protocol Expansion
* **V2Ray REALITY Verification**: Add specific checks for REALITY.
* **OpenVPN Support**: Add parsing for .ovpn files.
* **Shadowsocks-Rust Integration**: Use the official Rust core via FFI.

### 📊 Data Science & Analytics
* **Churn Prediction**: Analyze proxy survival rates.
* **Network Topology Mapping**: Visual latency triangulation.

## Development Guidelines

-   **No Placeholders**: Avoid `TODO` or incomplete code in the `main` branch.
-   **Testing**: Add unit tests for new logic. Use `hypothesis` for fuzz testing parsers.
-   **Security**: Do not commit API keys or secrets. Use environment variables.
-   **Documentation**: Update `README.md` or `ARCHITECTURE.md` if you change core functionality.

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0 License.
