# Contributing to ConfigStream

First off, **thank you** for considering a contribution to ConfigStream! 🎉

ConfigStream is not just a proxy scraper; it's a high-performance, data-driven platform dedicated to internet freedom. We aim to build the most robust, resilient, and accessible proxy aggregation system in the world, entirely on free infrastructure.

This document provides a comprehensive guide for contributors of all levels, from "Zero" to "Hero".

## 🌟 Guiding Principles

1.  **Zero Budget, Infinite Scale**: We rely solely on free-tier infrastructure (GitHub Actions, Pages, Public CDNs). Every feature must fit within these constraints (e.g., no persistent 24/7 servers, minimal artifact size).
2.  **Data Over Quantity**: We prefer 1,000 reliable, high-speed proxies over 100,000 dead ones. Quality scoring, deduplication, and latency testing are paramount.
3.  **Accessibility First**: The output must be usable by everyone, regardless of their technical skill or location. This means localized UIs, simple subscription links, and PWA support.
4.  **Security & Privacy**: We must never expose users to malicious nodes intentionally. Strict validation and sanitization of all parsed input are mandatory.

---

## 🚫 Architectural Constraints (Non-Negotiable)

To maintain the project's longevity and "Zero Budget" promise, the following constraints are **non-negotiable**. Please do not suggest features that violate these:

*   **No External Databases**: We cannot use AWS RDS, hosted MongoDB, or paid Redis. We use SQLite (artifacts) or flat files (JSON/CSV).
*   **No Backend Servers**: The "backend" is a pipeline that runs on GitHub Actions. The "frontend" must be a static SPA (Single Page Application). We cannot run a Python/Node.js API server 24/7.
*   **GitHub Ecosystem**: The entire lifecycle (Fetch -> Test -> Deploy) must happen within GitHub.

---

## 🚀 Roadmap & Next Steps

We have an ambitious vision. If you are looking for something to work on, here is our "Zero to Hero" roadmap.

### 🤖 Phase 1: Intelligence & Automation (Backend)
*   **Reinforcement Learning Scheduler**:
    *   *Goal*: Replace the current static retest intervals with an RL agent (e.g., Q-Learning) that learns the uptime patterns of each source.
    *   *Tech*: `scikit-learn`, `numpy`, SQLite.
*   **Predictive Anomaly Detection**:
    *   *Goal*: Use time-series forecasting (ARIMA/Prophet) to predict when a source is about to die based on its historical yield.
    *   *Impact*: Proactively remove dying sources before they break the build.
*   **Advanced Protocol Fingerprinting**:
    *   *Goal*: Use ML to identify the true protocol of an obfuscated stream (e.g., detecting VLESS disguised as HTTPS).

### 🌍 Phase 2: Access & Localization (Frontend)
*   **Smart Mirroring**:
    *   *Goal*: Automate deployment to decentralized networks (IPFS, Arweave) and alternative CDNs (Vercel, Netlify, GitLab Pages) to prevent censorship of the main repo.
    *   *Tooling*: `ipfs-car`, GitHub Actions Matrix.
*   **Telegram/Matrix Bot**:
    *   *Goal*: A bot that allows users to request a fresh proxy for a specific country directly via chat.
    *   *Note*: Must run statelessly or on edge functions (Cloudflare Workers).

### 🛠️ Phase 3: DevOps & Scale (Infrastructure)
*   **Distributed Worker Mesh**:
    *   *Goal*: Scale the pipeline across 50+ parallel GitHub Action jobs using a "Map-Reduce" pattern.
    *   *Challenge*: Efficiently merging 50+ SQLite databases or JSON artifacts without conflicts.
*   **Database Migration**:
    *   *Goal*: Migrate from SQLite to a cloud-native time-series database (e.g., InfluxDB Cloud Free Tier or Supabase) for long-term historical data analysis.

### 🛡️ Phase 4: Hardcore Security
*   **TLS Fingerprint Randomization (uTLS)**:
    *   *Goal*: Integrate a Go-based sidecar (via `cffi` or subprocess) to randomize TLS Client Hellos during testing to evade advanced firewalls that block Python's `ssl` module.
*   **Honey Pot Detection**:
    *   *Goal*: actively probe proxies for "fake" open ports or traffic interception behaviors before listing them.

### 🔌 Phase 5: Protocol Expansion
*   **Shadowsocks-Rust via FFI**:
    *   *Goal*: Replace the Python implementation of Shadowsocks testing with the official Rust core for 10x performance.
*   **Hysteria 2 Advanced**:
    *   *Goal*: Support for Hysteria 2 port hopping and masquerading validation.

---

## 💻 Development Setup

### Prerequisites
-   Python 3.10+
-   Node.js (for frontend tooling, optional)
-   Docker (optional, for local emulation)

### 1. Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/ConfigStream.git
cd ConfigStream
```

### 2. Install Dependencies
We use `pip` with strict pinning.
```bash
pip install -e ".[dev]"
```

### 3. Run the Pipeline Locally
To simulate a GitHub Actions run:
```bash
# Fetch and test proxies from batch 1
python -m configstream.cli merge --sources sources/batch_1.txt --output output/
```

### 4. Run the Frontend
```bash
python -m http.server -d frontend 8000
# Open http://localhost:8000
```

---

## 🧪 Testing & Quality Assurance

We maintain a high bar for code quality.

### Unit Tests
Running `pytest` is mandatory before pushing.
```bash
pytest tests/unit
```

### Fuzz Testing
We use `hypothesis` to fuzz our parsers. This ensures we don't crash on malformed input.
```bash
pytest tests/fuzz
```

### End-to-End (E2E) Tests
We use `playwright` to verify the frontend works as expected.
```bash
playwright install chromium
pytest tests/e2e
```

### Static Analysis
We use `mypy` for type checking and `flake8` for linting.
```bash
mypy src/
flake8 src/ tests/
```

---

## 📝 Documentation Guidelines

*   **Zero to Hero**: Documentation should explain *why*, not just *how*. Assume the reader is a junior developer.
*   **Visuals**: Use Mermaid diagrams for flows and architecture.
*   **Deep & Wide**: Cover every edge case. If you add a feature, document its limitations, performance implications, and configuration options.

---

## 🤝 Code of Conduct

Be kind. We are all here to build a free internet. Harassment or intolerance will not be tolerated.

---

**Happy Hacking!** 🚀
