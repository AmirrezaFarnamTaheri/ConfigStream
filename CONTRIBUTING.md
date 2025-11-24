# Contributing to ConfigStream

First off, thanks for taking the time to contribute! 🎉

ConfigStream is a community-driven project. We follow the "Zero Budget" philosophy: everything must run on free infrastructure (GitHub Actions/Pages).

## 🗺️ Roadmap & Future Work

We are actively looking for help with the following "Next Generation" features:

1.  **MTProto Crawler (Python/Telethon):**
    *   Currently, we scrape Telegram web previews (`t.me/s/...`).
    *   **Goal:** Implement a `Telethon` client to connect directly to Telegram's MTProto API. This would allow us to fetch `.conf` file attachments and access private channels.

2.  **Headless Validation:**
    *   Currently, we verify TCP/TLS connectivity.
    *   **Goal:** Add a "High Quality" tier verification using `playwright` to actually load a heavy webpage (e.g., Speedtest) through the proxy to prove it handles real web traffic.

3.  **Binary-Based Conversion:**
    *   Currently, we use Python adapters for output generation.
    *   **Goal:** Integrate the `subconverter` binary into our Docker image to support 10+ new client formats (Surfboard, Clash Verge) instantly.

## 🛠️ Development Setup

1.  **Fork the repo.**
2.  **Clone it locally.**
3.  **Install dependencies:**
    ```bash
    pip install -e ".[dev]"
    ```
4.  **Run Tests:**
    ```bash
    pytest
    ```

## 🏗️ Architecture & Structure

ConfigStream v2.0 is modular. Please respect the folder structure:

*   `src/configstream/pipeline_core/`: Core logic for sorting and output generation.
*   `src/configstream/plugins/`: Protocol parsers (add new protocols here).
*   `src/configstream/transport/`: Transport layers (Steganography, etc.).
*   `src/go/tester/`: High-performance Go components.

## 📝 Style Guide

*   **Python:** We use `black` and `flake8`.
*   **Type Hints:** All new code must be fully typed (`mypy`).
*   **Architecture:** Keep logic in `src/configstream/`. Do not put business logic in `scripts/`.

## 🤝 Pull Request Process

1.  Create a feature branch (`git checkout -b feature/amazing-feature`).
2.  Commit your changes.
3.  Run `pytest` to ensure nothing broke.
4.  Push to the branch.
5.  Open a Pull Request.

---
**Note:** By contributing, you agree that your code will be licensed under the AGPL-3.0 License.
