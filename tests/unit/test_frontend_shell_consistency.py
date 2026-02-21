# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ensure primary frontend pages share a consistent header/footer shell."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"

PRIMARY_PAGES = (
    "index.html",
    "proxies.html",
    "analytics.html",
    "lab.html",
    "wiki.html",
    "about.html",
)

REQUIRED_NAV_LINKS = (
    'href="index.html"',
    'href="proxies.html"',
    'href="analytics.html"',
    'href="lab.html"',
    'href="wiki.html"',
    'href="about.html"',
)


def test_primary_pages_have_consistent_shell() -> None:
    for page in PRIMARY_PAGES:
        text = (FRONTEND_DIR / page).read_text(encoding="utf-8")

        assert '<header class="header">' in text, page
        assert 'id="main-nav"' in text, page
        assert '<footer class="footer">' in text, page
        assert 'id="footerUpdate"' in text, page
        assert "assets/js/common-ui.js" in text, page

        for nav_link in REQUIRED_NAV_LINKS:
            assert nav_link in text, f"{page} missing nav link {nav_link}"
