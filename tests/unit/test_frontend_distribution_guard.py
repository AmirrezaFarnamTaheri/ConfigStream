# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static contracts for fail-closed public artifact distribution."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_primary_pages_load_distribution_guard_before_common_ui() -> None:
    for rel in ["index.html", "about.html", "analytics.html", "proxies.html", "lab.html", "wiki.html"]:
        text = (ROOT / "frontend" / rel).read_text(encoding="utf-8")
        guard = text.index('assets/js/artifact-state.js')
        common = text.find('assets/js/common-ui.js')
        main = text.find('assets/js/main.js')
        next_consumer = min(value for value in [common, main] if value >= 0)
        assert guard < next_consumer, rel


def test_guard_matches_canonical_health_contract_and_public_trust_rules() -> None:
    text = (ROOT / "frontend/assets/js/artifact-state.js").read_text(encoding="utf-8")
    assert "health?.status !== 'ok'" in text
    assert "health?.schema_validated !== true" in text
    assert "artifact contains no verified working proxies" in text
    assert "artifact is older than" in text
    assert "public artifact distribution requires HTTPS" in text
    assert "artifact signature verification key is not configured" in text
    assert "/^[0-9a-f]{40}$/" in text


def test_guard_scopes_controls_and_verifies_each_distributed_file() -> None:
    guard = (ROOT / "frontend/assets/js/artifact-state.js").read_text(encoding="utf-8")
    common = (ROOT / "frontend/assets/js/common-ui.js").read_text(encoding="utf-8")
    assert "const GUARDED_CONTROL_SELECTOR = '[data-file]'" in guard
    assert ".copy-btn, [data-file], a[download]" not in guard
    assert "fetchVerifiedJson" in guard
    assert "downloadVerifiedArtifact" in guard
    assert "crypto.subtle.digest('SHA-256', bytes)" in guard
    assert "hash does not match the signed manifest" in guard
    assert "size does not match the signed manifest" in guard
    assert "await artifact.verifyFile(targetFile)" in common
    assert "Copy blocked:" in common


def test_home_page_does_not_claim_auto_updating_before_verification() -> None:
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    main = (ROOT / "frontend/assets/js/main.js").read_text(encoding="utf-8")
    assert "Release data is unavailable until" in html
    assert "let sourceCount = null" in main
    assert "Artifact distribution is disabled" in main
