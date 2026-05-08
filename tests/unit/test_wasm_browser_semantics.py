# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression checks for browser-constrained WASM tester semantics."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


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
            _read("KNOWN_ISSUES.md"),
        ]
    )

    forbidden = [
        "WASM native network",
        "native network testing in WASM",
        "browser verification is equivalent",
        "equivalent to Go sidecar",
    ]
    for phrase in forbidden:
        assert phrase not in docs

    assert "browser-limited reachability" in docs.lower()
