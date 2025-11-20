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

## Roadmap & Needed Contributions

Looking for a place to start? Here are some areas where we could use your help:

### 🧠 Intelligence & Logic
-   **Reinforcement Learning**: Implement RL for the `SmartRetestScheduler` to dynamically optimize testing intervals based on network conditions.
-   **Advanced Anomaly Detection**: Improve the `AnomalyDetector` with more sophisticated statistical models (e.g., Isolation Forests) to catch subtle poisoning attacks.
-   **Source Scoring**: Refine the `SourceQualityTracker` algorithm to weigh sources by geo-diversity and protocol variety, not just uptime.

### 🔌 Protocols & Ecosystem
-   **New Protocols**: Add support for **SSH Tunnels**, **TUIC v5**, **Juicity**, or **Hysteria 1**.
-   **Client Adapters**: Create adapters for **Surge**, **Quantumult X**, and **Loon** configuration formats.
-   **Direct Integrations**: Build plugins or webhooks to push configs directly to Telegram, Discord, or Ntfy.

### 💻 Frontend & Dashboard
-   **Real-Time Updates**: Implement WebSockets (using FastAPI) to push live testing results to the dashboard without refreshing.
-   **Advanced Visualizations**: Add historical uptime charts, latency heatmaps (latency vs time of day), and world map visualizations.
-   **Localization (i18n)**: Translate the dashboard into Chinese, Russian, Farsi, and other languages.
-   **PWA Support**: Turn the dashboard into a Progressive Web App for mobile installability.

### 🛡️ Security & Hardening
-   **Active Probing**: Implement active MITM detection techniques (e.g., comparing certificate fingerprints against a trusted DoH source).
-   **Fingerprint Evasion**: Improve `singbox2proxy` configs to better mimic realistic browser traffic (uTLS randomization).
-   **Container Hardening**: Further lock down the Docker image (e.g., running as non-root, read-only filesystem).

### ⚙️ DevOps & Performance
-   **Kubernetes Support**: Create a Helm chart for scalable deployment on K8s clusters.
-   **Performance Tuning**: Optimize the Python `asyncio` loop or rewrite hot paths (like parsing) in Rust (via PyO3) for extreme speed.
-   **Multi-Arch Builds**: Ensure Docker images build and test correctly on ARM64 (Raspberry Pi, Apple Silicon).

## Development Guidelines

-   **No Placeholders**: Avoid `TODO` or incomplete code in the `main` branch.
-   **Testing**: Add unit tests for new logic. If you touch the parsers, run the fuzz tests.
-   **Security**: Do not commit API keys or secrets. Use environment variables.
-   **Documentation**: Update `README.md` or `ARCHITECTURE.md` if you change core functionality.

## Project Structure

-   `src/configstream/`: Core Python source code.
-   `frontend/`: Web dashboard assets (HTML/CSS/JS).
-   `tests/`: Unit and integration tests.
-   `sources/`: Text files containing proxy source URLs.

## License

By contributing, you agree that your contributions will be licensed under its GPL-3.0 License.
