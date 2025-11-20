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

We have an ambitious vision for ConfigStream. Below is a detailed breakdown of features, methods, and improvements we are looking for.

### 🧠 Intelligence & Data Science
* **Reinforcement Learning (RL) Scheduler**:
  * **Goal**: Move beyond fixed intervals for retesting.
  * **Method**: Implement an RL agent (e.g., Q-Learning) that learns the optimal retest frequency for each proxy based on its stability history, penalizing frequent checks on stable proxies to save bandwidth.
* **Advanced Anomaly Detection**:
  * **Goal**: Detect poisoning attacks (malicious nodes injecting fake proxies) with higher precision.
  * **Method**: Use `scikit-learn` to implement **Isolation Forests** or **One-Class SVM** on source yield statistics.
* **Smart Source Scoring**:
  * **Goal**: Rank sources not just by yield, but by "uniqueness" and "geo-diversity".
  * **Method**: Update `SourceQualityTracker` to calculate a Gini index for the country distribution of proxies provided by a source.

### 🔌 Protocol Support & Adapters
* **New Protocols**:
  * **SSH Tunnels**: Parse and test SSH credentials.
  * **TUIC v5 / Juicity**: Add support for these emerging high-performance protocols.
  * **Hysteria 2 Obfuscation**: Support advanced masquerading fields.
* **Client Adapters**:
  * **Surge / Loon / Quantumult X**: Write new serializer modules in `src/configstream/adapters.py` to export to these proprietary formats.
  * **SIP008**: Support the standardized Shadowsocks configuration delivery format.

### 💻 Frontend & Dashboard Widgets
* **Real-Time WebSocket Feed**:
  * **Goal**: Watch the pipeline working in real-time.
  * **Method**: Create a FastAPI WebSocket endpoint that broadcasts `Task` progress events to the frontend.
* **Interactive World Map**:
  * **Widget**: A D3.js or Leaflet.js map on the dashboard showing proxy locations.
  * **Feature**: Click a country to filter the list instantly.
* **Historical Charts**:
  * **Widget**: Chart.js or Recharts graphs showing "Total Working Proxies" over the last 24h/7d.
* **PWA (Progressive Web App)**:
  * **Enhancement**: Add `manifest.json` and Service Workers to allow installing the dashboard on mobile devices.

### 🛡️ Security Enhancements
* **Active MITM Detection**:
  * **Method**: During the connectivity test, verify the SSL certificate fingerprint of the target (e.g., google.com) against a known good value to detect interception.
* **Honey Pot Detection**:
  * **Method**: Identify proxies that redirect traffic to phishing pages or inject ads.
* **Dependency Hardening**:
  * **Enhancement**: Implement `hashin` or similar tools to enforce hash checking for all Python dependencies.

### ⚙️ DevOps & Infrastructure
* **Kubernetes Helm Chart**:
  * **Goal**: One-command deployment to K8s clusters.
  * **Feature**: Separate `worker` and `web` deployments with a shared `PersistentVolume` for the output.
* **Rust Acceleration**:
  * **Optimization**: Rewrite the hot-path parser logic (`src/configstream/parsers.py`) in Rust using `PyO3` for a 10x-50x speedup.
* **Multi-Architecture Docker Images**:
  * **Goal**: Support ARM64 natively (Raspberry Pi, Apple Silicon).

### 🧪 Testing & Verification
* **End-to-End (E2E) Tests**:
  * **Tool**: Playwright or Selenium.
  * **Goal**: Verify that the generated `proxies.json` can actually be loaded and rendered by the frontend.
* **Mock Server Expansion**:
  * **Improvement**: Enhance `tests/conftest.py` to mock a full V2Ray/Sing-box execution environment so we don't rely on external binaries for unit tests.

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
