# Contributor Guide

## The "Zero Budget" Constraint
ConfigStream is unique because it must run for **$0.00**.
If you contribute a feature that requires:
*   A paid API key
*   A persistent database (VPS, AWS RDS)
*   A paid hosting service

**It will be rejected.**

We innovate by using:
*   **GitHub Actions** for compute.
*   **GitHub Pages** for hosting.
*   **SQLite Artifacts** for state.
*   **Client-Side Compute (WASM)** for scale.

## Code Standards
*   **No Monoliths:** Files should be under 500 lines.
*   **Type Hints:** All Python code must be fully typed (`mypy` strict).
*   **Tests:** New features must have unit tests. Coverage must remain >90% (Target 98%).
*   **No Active Scanning:** Do not add code that scans ports or attacks servers.

## Pull Request Process
1.  Fork the repo.
2.  Install dev dependencies: `pip install -e ".[dev]"`
3.  Run tests: `pytest`
4.  Submit PR with a description of how your change respects the Zero Budget constraint.
