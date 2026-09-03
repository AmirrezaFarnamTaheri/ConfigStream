# SPDX-License-Identifier: AGPL-3.0-or-later
"""Automated regression tests for frontend trust bootstrap sequence.

Standardizes script inclusion order across all public static HTML surfaces:
untime-config.js -> constants.js -> erifier.js -> rtifact-state.js / rtifact-guard.js
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"

PUBLIC_ONLINE_PAGES = (
    FRONTEND_DIR / "index.html",
    FRONTEND_DIR / "proxies.html",
    FRONTEND_DIR / "analytics.html",
    FRONTEND_DIR / "lab.html",
    FRONTEND_DIR / "about.html",
    FRONTEND_DIR / "evidence.html",
    FRONTEND_DIR / "wiki.html",
    REPO_ROOT / "architecture.html",
)

OFFLINE_EXEMPT_PAGES = (
    FRONTEND_DIR / "lab-offline.html",
)


def get_script_sources(html: str) -> list[tuple[str, set[str]]]:
    """Extract script sources and loading attributes in document order."""
    sources: list[tuple[str, set[str]]] = []
    for match in re.finditer(r"<script\b(?P<attributes>[^>]*)>", html, flags=re.IGNORECASE):
        attributes = match.group("attributes")
        source = re.search(r"\bsrc=[\"']([^\"']+)[\"']", attributes, flags=re.IGNORECASE)
        if source:
            flags = {
                flag
                for flag in ("async", "defer")
                if re.search(rf"(?:^|\s){flag}(?:\s|=|$)", attributes, flags=re.IGNORECASE)
            }
            sources.append((source.group(1), flags))
    return sources


def find_script_index(scripts: list[tuple[str, set[str]]], script_name: str) -> int:
    """Find 0-based index of first script whose path ends with script_name."""
    for idx, (src, _flags) in enumerate(scripts):
        clean_src = src.split("?")[0].strip()
        if clean_src == script_name or clean_src.endswith("/" + script_name):
            return idx
    return -1


def audit_trust_bootstrap(html: str) -> list[str]:
    """Audit script loading sequence for trust bootstrap compliance.

    Returns a list of violation messages (empty list means fully compliant).
    """
    scripts = get_script_sources(html)
    violations: list[str] = []

    runtime_idx = find_script_index(scripts, "runtime-config.js")
    constants_idx = find_script_index(scripts, "constants.js")
    verifier_idx = find_script_index(scripts, "verifier.js")

    if runtime_idx == -1:
        violations.append("Missing runtime-config.js")
    if constants_idx == -1:
        violations.append("Missing constants.js")
    if verifier_idx == -1:
        violations.append("Missing verifier.js")

    if runtime_idx != -1 and constants_idx != -1 and runtime_idx > constants_idx:
        violations.append(
            f"runtime-config.js (index {runtime_idx}) loaded after constants.js (index {constants_idx})"
        )

    if constants_idx != -1 and verifier_idx != -1 and constants_idx > verifier_idx:
        violations.append(
            f"constants.js (index {constants_idx}) loaded after verifier.js (index {verifier_idx})"
        )

    if runtime_idx != -1 and verifier_idx != -1 and runtime_idx > verifier_idx:
        violations.append(
            f"runtime-config.js (index {runtime_idx}) loaded after verifier.js (index {verifier_idx})"
        )

    for script_name in ("runtime-config.js", "constants.js", "verifier.js"):
        script_idx = find_script_index(scripts, script_name)
        if script_idx != -1 and scripts[script_idx][1]:
            flags = ", ".join(sorted(scripts[script_idx][1]))
            violations.append(f"{script_name} must not use async/defer ({flags})")

    # If artifact guard / artifact state is present, it must be loaded after verifier.js
    for guard_name in ("artifact-state.js", "artifact-guard.js"):
        guard_idx = find_script_index(scripts, guard_name)
        if guard_idx != -1:
            if verifier_idx == -1:
                violations.append(f"{guard_name} loaded without verifier.js")
            elif guard_idx < verifier_idx:
                violations.append(
                    f"{guard_name} (index {guard_idx}) loaded before verifier.js (index {verifier_idx})"
                )

    return violations


@pytest.mark.parametrize("page_path", PUBLIC_ONLINE_PAGES, ids=lambda p: p.name)
def test_public_pages_enforce_trust_bootstrap_sequence(page_path: Path) -> None:
    """Verify that all public online HTML pages strictly adhere to the trust bootstrap sequence."""
    assert page_path.is_file(), f"Page file does not exist: {page_path}"
    html = page_path.read_text(encoding="utf-8")
    violations = audit_trust_bootstrap(html)
    assert not violations, f"{page_path.name} failed trust bootstrap audit:\n" + "\n".join(f"- {v}" for v in violations)


def test_offline_lab_page_is_exempt_and_self_contained() -> None:
    """Verify that lab-offline.html is an offline-exempt surface with no external script fetches."""
    offline_page = FRONTEND_DIR / "lab-offline.html"
    assert offline_page.is_file()
    html = offline_page.read_text(encoding="utf-8")
    scripts = get_script_sources(html)
    assert len(scripts) == 0, f"lab-offline.html must not load external scripts, found: {scripts}"
    assert "connect-src 'none'" in html, "lab-offline.html must enforce connect-src 'none' in CSP"


@pytest.mark.parametrize(
    "html_fixture, expected_violation",
    [
        (
            '<script src="assets/js/constants.js"></script><script src="assets/js/verifier.js"></script>',
            "Missing runtime-config.js",
        ),
        (
            '<script src="assets/js/runtime-config.js"></script><script src="assets/js/verifier.js"></script>',
            "Missing constants.js",
        ),
        (
            '<script src="assets/js/runtime-config.js"></script><script src="assets/js/constants.js"></script>',
            "Missing verifier.js",
        ),
        (
            '<script src="assets/js/constants.js"></script><script src="assets/js/runtime-config.js"></script><script src="assets/js/verifier.js"></script>',
            "runtime-config.js (index 1) loaded after constants.js (index 0)",
        ),
        (
            '<script src="assets/js/runtime-config.js"></script><script src="assets/js/verifier.js"></script><script src="assets/js/constants.js"></script>',
            "constants.js (index 2) loaded after verifier.js (index 1)",
        ),
        (
            '<script src="assets/js/runtime-config.js"></script><script src="assets/js/artifact-state.js"></script><script src="assets/js/constants.js"></script><script src="assets/js/verifier.js"></script>',
            "artifact-state.js (index 1) loaded before verifier.js (index 3)",
        ),
        (
            '<script defer src="assets/js/runtime-config.js"></script><script src="assets/js/constants.js"></script><script src="assets/js/verifier.js"></script>',
            "runtime-config.js must not use async/defer (defer)",
        ),
        (
            '<script src="assets/js/runtime-config.js"></script><script async src="assets/js/constants.js"></script><script src="assets/js/verifier.js"></script>',
            "constants.js must not use async/defer (async)",
        ),
    ],
)
def test_trust_bootstrap_audit_negative_vectors(html_fixture: str, expected_violation: str) -> None:
    """Verify that malformed or incomplete trust bootstrap sequences fail the audit."""
    violations = audit_trust_bootstrap(html_fixture)
    assert any(expected_violation in v for v in violations), f"Expected '{expected_violation}', got: {violations}"
