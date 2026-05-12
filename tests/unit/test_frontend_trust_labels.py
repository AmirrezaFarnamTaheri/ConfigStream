# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"


def test_frontend_stats_labels_do_not_overclaim_verification() -> None:
    index_html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    analytics_html = (FRONTEND_DIR / "analytics.html").read_text(encoding="utf-8")
    i18n_js = (FRONTEND_DIR / "assets/js/i18n.js").read_text(encoding="utf-8")
    combined = "\n".join([index_html, analytics_html, i18n_js])

    assert "Unique &amp; Verified" not in index_html
    assert "Unique & Verified" not in combined
    assert "Online Now" not in combined
    assert "Currently Online" not in combined
    assert "Retested Working" in combined
    assert "Unique Candidates" in combined


def test_frontend_shielded_copy_marks_candidates() -> None:
    index_html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    analytics_html = (FRONTEND_DIR / "analytics.html").read_text(encoding="utf-8")

    assert "Shielded Candidates" in index_html
    assert "Shielded Candidates" in analytics_html
    assert "shielded chains that work" not in index_html
    assert "shielded candidate chains" in index_html
    assert "candidate chain configs" in index_html


def test_frontend_shielded_rows_render_as_candidates_not_online() -> None:
    proxies_js = (FRONTEND_DIR / "assets/js/proxies.js").read_text(encoding="utf-8")
    style_css = (FRONTEND_DIR / "assets/css/style.css").read_text(encoding="utf-8")

    assert "const isCandidateOnly = isShielded && !shieldedVerified;" in proxies_js
    assert "const effectiveIsWorking = Boolean(raw.is_working) && !isCandidateOnly;" in proxies_js
    assert "isCandidateOnly ? 'status-candidate'" in proxies_js
    assert "isCandidateOnly ? 'Candidate'" in proxies_js
    assert "row.className = p.effectiveIsWorking" in proxies_js
    assert ".status-badge.status-candidate" in style_css
