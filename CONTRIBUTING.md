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
3.  **Install dependencies** (pinned, exactly as CI does):
    ```bash
    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements-dev.txt
    pip install -e . --no-deps
    pre-commit install                      # optional but recommended
    ```
4.  **Run Tests:**
    ```bash
    pytest -m "not playwright and not frontend_browser and not e2e"   # fast, no browser
    pytest                                                             # full suite
    ```

    WSL note: If `pytest` crashes with a `FileNotFoundError` inside `_pytest/capture.py`, your temp directory may be on a Windows mount (e.g. `/mnt/c/...`). Run tests with a Linux temp dir:
    ```bash
    TMPDIR=/tmp TEMP=/tmp TMP=/tmp pytest
    ```

## 🏗️ Architecture & Structure

ConfigStream v3.0 is modular. Please respect the folder structure:

*   `src/configstream/`: Main package. Contains pipeline logic (`producer.py`, `consumer.py`), output handler, and stats.
*   `src/configstream/parsers/`: Protocol parsers (add new protocols here).
*   `src/configstream/converters/`: Sing-box, Clash, and common conversion logic.
*   `src/configstream/intelligence/`: Chaining, evasion, washer, and DNS lists.
*   `src/configstream/stego.py`: Steganography logic.
*   `src/go/tester/`: High-performance Go proxy tester.

## 📝 Style Guide

*   **Python:** We use `black` and `flake8`.
*   **Type Hints:** All new code must be fully typed (`mypy`).
*   **Architecture:** Keep logic in `src/configstream/`. Do not put business logic in `scripts/`.

## ✅ Before You Push

CI blocks on the same checks you can run locally:

```bash
black --check --target-version py310 $(git diff --name-only origin/main -- '*.py')
flake8 src/ tests/
mypy .
python scripts/generate_debt_matrix.py     # regenerates docs/DEBT_MATRIX.md + docs/debt_matrix.json
python scripts/generate_triage_report.py   # regenerates TRIAGE_REPORT.md
python scripts/verify_repository.py --profile static
```

The debt matrix records the line number of every broad `except` and
debt marker comment (see `scripts/generate_debt_matrix.py`), so **almost any Python edit makes it stale**; commit the
regenerated files with your change. `pre-commit run --all-files` does all of
the above (the `pytest` hook runs on `pre-push`).

Frontend changes: `npm ci && npm run build && npm run test:frontend:no-network`
(set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` if Playwright cannot download Chromium).

## 🤝 Pull Request Process

1.  Create a feature branch (`git checkout -b feature/amazing-feature`).
2.  Commit your changes.
3.  Run `pytest` to ensure nothing broke.
4.  Push to the branch.
5.  Open a Pull Request.

---
**Note:** By contributing, you agree that your code will be licensed under the AGPL-3.0 License.
