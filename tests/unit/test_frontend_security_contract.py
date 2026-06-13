# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression guards for frontend CSP and Lab export safety."""

from __future__ import annotations

from pathlib import Path
import re

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
    lab_js = _read(FRONTEND_DIR / "assets" / "js" / "lab" / "exporters.js")

    # Bash export must not use inline remote install/extract.
    assert 'curl -sL "$URL" | tar xz' not in lab_js

    # Python export must not auto-download archives.
    assert "urllib.request.urlretrieve" not in lab_js
    assert "tar.extractall" not in lab_js

    # Generated scripts should require a preinstalled sing-box binary.
    assert "sing-box not found in PATH" in lab_js


def test_project_frontend_avoids_raw_inner_html_assignment() -> None:
    offenders: list[str] = []
    assignment_re = re.compile(r"\.\s*innerHTML\s*=")
    paths = list((FRONTEND_DIR / "assets/js").rglob("*.js"))
    paths.extend(FRONTEND_DIR.glob("*.html"))
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        if "/utils/qrcode.js" in rel:
            continue
        if "/assets/libs/" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            if assignment_re.search(line):
                offenders.append(f"{rel}:{line_no}")

    assert offenders == []


def test_frontend_html_avoids_inline_event_handlers() -> None:
    offenders: list[str] = []
    inline_handler_re = re.compile(
        r"\bon(?:click|change|submit|input|keydown|keyup|load|error)\s*=",
        re.IGNORECASE,
    )
    for path in FRONTEND_DIR.glob("*.html"):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            if inline_handler_re.search(line):
                offenders.append(f"{rel}:{line_no}")

    assert offenders == []
