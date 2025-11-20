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
    mypy src tests
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

We have an ambitious vision for ConfigStream to become the definitive open-source platform for internet freedom. Below is a comprehensive breakdown of our future goals, divided by domain. We invite you to pick a task and contribute!

### 🎨 Frontend & UI/UX
*   **Visualizations**: Implement a 3D Globe view (using `three.js` or `globe.gl`) to visualize active proxy nodes in real-time.
*   **PWA Enhancements**: Add offline support for viewing previously fetched proxies and background sync.
*   **Accessibility (a11y)**: Achieve WCAG 2.1 AA compliance. Add keyboard shortcuts for power users.
*   **Customization**: Allow users to save their preferred filters and theme settings to local storage.
*   **I18n**: Implement a robust internationalization framework to support Chinese, Russian, Farsi, and Arabic.

### 🤖 AI & Intelligence
*   **Smart Scheduler**: Implement a Reinforcement Learning (RL) agent (e.g., Q-Learning) to dynamically adjust retest intervals based on proxy stability history.
*   **Anomaly Detection**: Use time-series analysis (Prophet/ARIMA) to predict source failures or censorship events before they happen.
*   **Protocol Fingerprinting**: Use ML models to identify the true protocol of obfuscated streams or detect "fake" working proxies (honeypots).
*   **Natural Language Query**: Allow users to search for proxies using natural language (e.g., "fastest US servers for streaming").

### 🛡️ Security & Privacy
*   **Advanced Honeypot Detection**: Analyze traffic patterns and server headers to identify state-sponsored honeypots.
*   **TLS Fingerprint Randomization**: Randomize uTLS fingerprints during testing to avoid detection by active probes.
*   **Malware Scanning**: Integrate deeper with VirusTotal or similar APIs to scan destination IPs for known malware hosts.
*   **DPI Evasion**: Implement advanced fragmentation and padding strategies in the testing client.

### 🔌 Protocol Support
*   **V2Ray REALITY**: Add specific verification steps for REALITY (checking `pbk`, `sid`, and fingerprint).
*   **OpenVPN**: Add robust parsing and testing for `.ovpn` files.
*   **WireGuard**: Improve WireGuard testing with custom MTU and reserved bytes handling.
*   **Shadowsocks-Rust**: Integrate the official Rust core via FFI for higher performance testing.

### 🛠️ Infrastructure & DevOps
*   **Distributed Workers**: Scale the pipeline across multiple nodes/containers using Celery or a custom distributor.
*   **Database Migration**: Migrate from SQLite to PostgreSQL/TimescaleDB for handling millions of historical records.
*   **Observability**: Integrate a full Prometheus/Grafana stack for real-time pipeline monitoring.
*   **IPFS/Arweave**: Automate publishing of configurations to decentralized storage networks to prevent censorship.

### 📊 Data Science
*   **Churn Prediction**: Analyze survival rates of proxies to predict when a node will go offline.
*   **Network Topology**: Map the latency between nodes to triangulate network bottlenecks or censorship firewalls.
*   **Source Scoring**: Develop a "Trust Score" for every public source based on long-term reliability and safety.

## Development Guidelines

-   **No Placeholders**: Avoid `TODO` or incomplete code in the `main` branch.
-   **Testing**: Add unit tests for new logic. Use `hypothesis` for fuzz testing parsers.
-   **Security**: Do not commit API keys or secrets. Use environment variables.
-   **Documentation**: Update `README.md`, `ARCHITECTURE.md`, or `docs/WIKI.md` if you change core functionality.

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0 License.
