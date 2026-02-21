# SPDX-License-Identifier: AGPL-3.0-or-later
"""Basic documentation hygiene checks for stale non-functional content."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


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
    known_issues = _read("KNOWN_ISSUES.md")
    assert "particularly the Go WASM networking limitation" not in known_issues


def test_status_does_not_list_removed_fetcher_py_as_consolidated() -> None:
    status = _read("STATUS.md")
    assert "dns_prewarm.py" in status
    assert "fetcher_core/" in status
    assert "pipeline_stages.py" in status
    assert "dns_prewarm.py, fetcher.py, output.py" not in status
