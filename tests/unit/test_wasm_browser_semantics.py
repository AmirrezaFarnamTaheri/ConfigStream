# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression checks for browser-constrained WASM tester semantics."""

from __future__ import annotations

from pathlib import Path

from tests.unit.doc_sources import read_doc, read_first_existing_doc

ROOT = Path(__file__).resolve().parents[2]
KNOWN_ISSUES_SOURCES = [
    "KNOWN_ISSUES.md",
    "docs/history/source-of-truth/ConfigStream_Master_Audit_Report - Main SOURCE OF TRUTH.md",
]


def _read(path: str) -> str:
    return read_doc(ROOT, path)


def test_wasm_go_tester_reports_browser_limited_url_failures() -> None:
    source = _read("src/go/tester/wasm_main.go")

    assert "normalizeBrowserReachabilityURL" in source
    assert "Unsupported browser reachability scheme" in source
    assert "Invalid URL" in source
    assert 'parsed.Scheme != "ws" && parsed.Scheme != "wss"' in source
    assert "WebSocket" in source


def test_frontend_labels_wasm_as_browser_limited() -> None:
    loader = _read("frontend/assets/js/wasm_loader.js")

    assert "Browser-limited reachability check" in loader
    assert "browser-check-unsupported" in loader
    assert "browser-limited" in loader
    assert "native proxy handshakes" in loader


def test_docs_do_not_claim_wasm_native_network_testing() -> None:
    docs = "\n".join(
        [
            _read("README.md"),
            _read("docs/wiki/project/01-introduction.md"),
            _read("docs/wiki/project/02-architecture.md"),
            _read("docs/wiki/project/04-engineering.md"),
            read_first_existing_doc(ROOT, KNOWN_ISSUES_SOURCES),
        ]
    )

    forbidden = [
        "WASM native network",
        "native network testing in WASM",
        "browser verification is equivalent",
        "browser verification is equivalent to Go sidecar",
    ]
    for phrase in forbidden:
        assert phrase not in docs

    assert "browser-limited reachability" in docs.lower()
