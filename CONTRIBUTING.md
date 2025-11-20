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

### 🌍 Localization & Access
* **Multi-Language Dashboard**:
  * **Goal**: Add i18n support to the frontend (Chinese, Persian, Russian).
* **Censorship Resistance**:
  * **Goal**: Implement domain fronting or mirror rotation logic for the update checker.

### 🛠️ Infrastructure
* **Distributed Workers**:
  * **Goal**: Scale the pipeline across multiple nodes using Celery or Redis Queues.
* **Database Migration**:
  * **Goal**: Migrate from SQLite to PostgreSQL for high-concurrency deployments.

### 🛡️ Advanced Security
* **TLS Fingerprint Randomization**:
  * **Goal**: Randomize uTLS fingerprints during testing to avoid active probing detection.
* **Deep Packet Inspection (DPI) Evasion**:
  * **Goal**: Implement fragmentation strategies in the tester to verify DPI bypass capabilities.

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
