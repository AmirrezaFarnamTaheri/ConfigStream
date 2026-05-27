# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression guards for frontend CSP and Lab export safety."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_frontend_csp_disables_unsafe_eval() -> None:
    pages = [
        "index.html",
        "about.html",
        "analytics.html",
        "lab.html",
        "proxies.html",
        "wiki.html",
    ]
    for page in pages:
        html = _read(FRONTEND_DIR / page)
        assert "unsafe-eval" not in html, f"{page} still allows unsafe-eval"


def test_lab_csp_allows_network_diagnosis_endpoints() -> None:
    html = _read(FRONTEND_DIR / "lab.html")
    required = [
        "https://cp.cloudflare.com",
        "https://connectivitycheck.gstatic.com",
        "https://api.github.com",
        "https://en.wikipedia.org",
        "https://cloudflare-dns.com",
    ]
    for endpoint in required:
        assert endpoint in html, f"Lab CSP is missing connect-src endpoint: {endpoint}"


def test_lab_generated_scripts_do_not_auto_download_binaries() -> None:
    lab_js = _read(FRONTEND_DIR / "assets" / "js" / "lab.js")

    # Bash export must not use inline remote install/extract.
    assert "curl -sL \"$URL\" | tar xz" not in lab_js

    # Python export must not auto-download archives.
    assert "urllib.request.urlretrieve" not in lab_js
    assert "tar.extractall" not in lab_js

    # Generated scripts should require a preinstalled sing-box binary.
    assert "sing-box not found in PATH" in lab_js
