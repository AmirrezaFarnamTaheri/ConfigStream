# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path


def test_ci_audits_python_node_go_and_rust_dependencies() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "pip-audit -r requirements-prod.txt" in workflow
    assert "npm audit --audit-level=high" in workflow
    assert "golang.org/x/vuln/cmd/govulncheck@v1.1.4" in workflow
    assert "cargo install cargo-audit --version 0.22.2 --locked" in workflow
    assert "cargo audit --file src/rust/ss_checker/Cargo.lock" in workflow
