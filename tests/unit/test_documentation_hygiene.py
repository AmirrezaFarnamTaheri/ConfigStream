# SPDX-License-Identifier: AGPL-3.0-or-later
"""Basic documentation hygiene checks for stale non-functional content."""

from __future__ import annotations

from pathlib import Path

from tests.unit.doc_sources import read_doc, read_first_existing_doc

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWN_ISSUES_SOURCES = [
    "KNOWN_ISSUES.md",
    "ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md",
]


def _read(rel_path: str) -> str:
    return read_doc(REPO_ROOT, rel_path)


def test_readme_uses_metadata_json_for_freshness_check() -> None:
    readme = _read("README.md")
    assert "Frontend shows stale data" in readme
    assert "`metadata.json`" in readme
    assert "timestamps in `proxies.json`" not in readme


def test_frontend_docs_reference_vendored_libs_path() -> None:
    frontend_doc = _read("docs/wiki/project/06-frontend.md")
    assert "assets/libs/" in frontend_doc
    assert "assets/js/lib/" not in frontend_doc


def test_known_issues_does_not_reference_resolved_wasm_limitation_as_open() -> None:
    known_issues = read_first_existing_doc(REPO_ROOT, KNOWN_ISSUES_SOURCES)

    assert "particularly the Go WASM networking limitation" not in known_issues
    assert "browser-limited reachability checks" in known_issues
    assert "sidecar/Python test results remain authoritative" in known_issues


def test_status_reflects_production_ready_state() -> None:
    """STATUS.md must reflect the closed production gate and not carry stale
    remediation-in-progress language that contradicts the current verdict."""
    status = _read("STATUS.md")
    # Production gate is closed — these stale phrases must not appear.
    assert "Remediation in progress" not in status
    assert "not production-ready" not in status.lower()
    # The closed gate must be explicitly stated.
    assert "production" in status.lower()
    # Stale consolidated-file references must not appear.
    assert "dns_prewarm.py, fetcher.py, output.py" not in status


def test_public_claims_reflect_closed_production_gate() -> None:
    pyproject = _read("pyproject.toml")
    readme = _read("README.md")

    assert "Development Status :: 5 - Production/Stable" in pyproject
    assert "Development Status :: 4 - Beta" not in pyproject
    assert "production-ready as of v3.1.0" in readme
    assert "older production-ready claims are superseded" not in readme
    assert "TLS Fragmentation**: Splits TLS packets" not in readme
    assert "TLS Fragmentation**: Disabled" in readme


def test_readme_describes_proxies_json_as_array_not_metadata_envelope() -> None:
    readme = _read("README.md")

    assert "proxies.json: full dataset with metadata" not in readme
    assert "Full dataset with metadata" not in readme
    assert "`proxies.json` is always a JSON array" in readme
    assert "metadata lives in metadata.json" in readme


def test_docs_match_runtime_security_defaults() -> None:
    readme = _read("README.md")
    config_doc = _read("docs/wiki/project/Configuration.md")

    assert "USE_VWARP_TUNNEL=true (default: false)" not in readme
    assert "USE_VWARP_TUNNEL=true (default: true)" in readme
    assert "Required in production" in config_doc
    assert "production admin endpoints fail closed" in config_doc
