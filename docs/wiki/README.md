# ConfigStream Zero to Hero Guide

Welcome to the definitive guide for **ConfigStream**, the high-performance, automated proxy aggregation platform. This wiki is designed to take you from a complete beginner to a core contributor, explaining every technical decision, protocol detail, and engineering trick we use.

## Table of Contents

1. [**Introduction & Philosophy**](01-introduction.md)
   - Why ConfigStream exists.
   - The "Zero Budget" Architecture.
2. [**System Architecture**](02-architecture.md)
   - The Pipeline: Fetch, Parse, Test, Output.
   - AsyncIO Design Patterns.
   - Memory Management in Python.
3. [**Protocol Deep Dive**](03-protocols.md)
   - VLESS & REALITY: The new standard.
   - VMess, Trojan, Shadowsocks.
   - Parsing Logic & Regex vs. URL parsing.
4. [**Engineering Tricks**](04-engineering.md)
   - Adaptive Timeouts (TCP Congestion Control analogy).
   - Hedged Requests (Reducing tail latency).
   - Circuit Breakers & Rate Limiting.
5. [**DevOps & CI/CD**](05-devops.md)
   - GitHub Actions Matrix Strategy.
   - Caching Strategies (SQLite, artifacts).
   - IPFS & Decentralization.
6. [**Frontend Development**](06-frontend.md)
   - Vanilla JS SPA architecture.
   - 3D Visualization with Three.js/Globe.gl.
   - PWA Implementation.

## Quick Start

To run the pipeline locally:

```bash
# 1. Install dependencies
pip install -e .[dev]

# 2. Run the pipeline
python -m configstream.cli merge --sources sources/batch_1.txt --output output/
```

## Contribution

We welcome all contributions! Please read [CONTRIBUTING.md](../../CONTRIBUTING.md) first.
