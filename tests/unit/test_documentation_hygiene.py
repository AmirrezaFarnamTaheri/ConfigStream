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


def test_status_reflects_current_blocked_release_state() -> None:
    """STATUS.md must follow current CI and live-deployment evidence."""
    status = _read("STATUS.md")
    normalized = status.lower()
    assert "not production-ready" in normalized
    assert "repository production gate | **open**" in normalized
    assert "release gate | **blocked**" in normalized
    assert "remediation in progress" in normalized
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
    assert "docs/history/source-of-truth/ConfigStream_Master_Audit_Report" not in readme
    assert (
        "Historical source-of-truth ledgers were absorbed into the master report and removed"
        in readme
    )
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


def test_master_records_second_pass_history_absorption() -> None:
    master = _read("ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md")

    required = [
        "Second-pass detailed absorption coverage",
        "674 headings and 2,800 obligation/caveat/action lines",
        "source content classification",
        "stale-cache retest policy",
        "smart-chain planning",
        "safe censorship diagnostics",
        "streaming parser/adaptive concurrency",
        "chaos testing",
        "Lab-abuse threat modeling",
        "visual regression/golden outputs",
        "subsystem health/admin/WebSocket eventing",
        "benchmark/memory profiling",
    ]
    for phrase in required:
        assert phrase in master


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


def test_project_tree_graph_html_structure() -> None:
    """docs/project_tree_graph.html must have valid HTML structure with style, head, and body tags in order."""
    html = _read("docs/project_tree_graph.html")
    assert "</style>" in html
    assert "</head>" in html
    assert "<body>" in html
    style_end = html.find("</style>")
    head_end = html.find("</head>")
    body_start = html.find("<body>")
    assert -1 < style_end < head_end < body_start
    assert "vis-network@9.1.2" in html
    assert "Visualization Engine Unavailable" in html


def test_docs_match_runtime_security_defaults() -> None:
    readme = _read("README.md")
    config_doc = _read("docs/wiki/project/Configuration.md")
    assert "USE_VWARP_TUNNEL=true" in readme
    assert "`USE_VWARP_TUNNEL` | `true`" in config_doc
    assert "Required in production" in config_doc
    assert "production admin endpoints fail closed" in config_doc
