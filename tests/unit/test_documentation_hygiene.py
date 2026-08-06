# SPDX-License-Identifier: AGPL-3.0-or-later
"""Basic documentation hygiene checks for stale non-functional content."""

from __future__ import annotations

from pathlib import Path

from tests.unit.doc_sources import read_doc

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_status_is_generated_from_machine_readable_readiness() -> None:
    status = _read("STATUS.md")
    readme = _read("README.md")
    pyproject = _read("pyproject.toml")

    assert "Generated from `docs/readiness.json`" in status
    assert "**Verdict:** CONDITIONAL" in status
    assert "**Production ready:** No" in status
    assert "Development Status :: 4 - Beta" in pyproject
    assert "Development Status :: 5 - Production/Stable" not in pyproject
    assert "conditional release candidate" in readme
    assert "not a verified production release" in readme
    assert "production-ready as of v3.1.0" not in readme
    assert "TLS Fragmentation**: Disabled" in readme
    assert "unblockable" not in readme.lower()
    assert "Upgrade to Platinum" not in readme


def test_active_docs_do_not_use_archived_ledgers_as_current_sources() -> None:
    active_paths = [
        "README.md",
        "STATUS.md",
        "AGENTS.md",
        "GEMINI.md",
        "docs/capability_registry.json",
        "docs/claim_ledger.json",
        "docs/module_ownership.json",
    ]
    forbidden = [
        "docs/history/source-of-truth/",
        "Historical audit ledgers under",
        "Historical ledgers under",
    ]
    for rel_path in active_paths:
        text = _read(rel_path)
        for phrase in forbidden:
            assert (
                phrase not in text
            ), f"{rel_path} still cites removed historical source {phrase}"


def test_active_docs_avoid_overclaiming_trust_language() -> None:
    active_paths = [
        "README.md",
        "docs/CENSORSHIP_EVASION.md",
        "docs/wiki/project/02-architecture.md",
        "docs/wiki/project/05-devops.md",
        "docs/wiki/project/06-frontend.md",
        "SECURITY.md",
    ]
    forbidden = [
        "Upgrade to Platinum",
        "Platinum Tier",
        "unblockable",
        "complete list of vetted proxies",
        "80+ innerHTML usages sanitized",
        "ConfigStream is in remediation",
        "full production gate remains open",
    ]
    for rel_path in active_paths:
        text = _read(rel_path)
        for phrase in forbidden:
            assert phrase not in text, f"{rel_path} contains stale phrase {phrase!r}"


def test_readme_describes_proxies_json_as_array_not_metadata_envelope() -> None:
    readme = _read("README.md")
    assert "proxies.json: full dataset with metadata" not in readme
    assert "Full dataset with metadata" not in readme
    assert "`proxies.json` is always a JSON array" in readme
    assert "metadata lives in metadata.json" in readme


def test_docs_match_runtime_security_defaults() -> None:
    readme = _read("README.md")
    config_doc = _read("docs/wiki/project/Configuration.md")
    assert "USE_VWARP_TUNNEL=true" in readme
    assert "`USE_VWARP_TUNNEL` | `true`" in config_doc
    assert "Required in production" in config_doc
    assert "production admin endpoints fail closed" in config_doc
