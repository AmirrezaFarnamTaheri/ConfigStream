# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ci_audits_python_node_go_and_rust_dependencies() -> None:
    ci_workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    security_workflow = (
        REPO_ROOT / ".github/workflows/dependency-security.yml"
    ).read_text(encoding="utf-8")

    assert "pip-audit -r requirements-prod.txt" in ci_workflow
    assert "npm audit --audit-level=high" in security_workflow
    assert "golang.org/x/vuln/cmd/govulncheck@v1.1.4" in security_workflow
    assert "cargo install cargo-audit --version 0.22.2 --locked" in security_workflow
    assert "cargo audit --file src/rust/ss_checker/Cargo.lock" in security_workflow
