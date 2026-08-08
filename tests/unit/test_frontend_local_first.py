# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
import hashlib
import json

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"

PRIMARY_PAGES = (
    "index.html",
    "about.html",
    "analytics.html",
    "proxies.html",
    "lab.html",
    "wiki.html",
)

FORBIDDEN_RUNTIME_HOSTS = (
    "unpkg.com",
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "flagcdn.com",
    "raw.githubusercontent.com",
    "api.qrserver.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
)

REQUIRED_LOCAL_ASSETS = (
    "assets/libs/feather.min.js",
    "assets/libs/three.min.js",
    "assets/libs/globe.gl.min.js",
    "assets/libs/chart.min.js",
    "assets/libs/pako.min.js",
    "assets/libs/fernetBrowser.min.js",
    "assets/libs/marked.min.js",
    "assets/libs/purify.min.js",
    "assets/libs/highlight.min.js",
    "assets/libs/atom-one-dark.min.css",
    "assets/js/runtime-config.js",
    "assets/images/globe/earth-blue-marble.jpg",
    "assets/images/globe/earth-night.jpg",
    "assets/images/globe/earth-topology.png",
    "assets/images/globe/night-sky.png",
    "assets/images/flags/w20/us.png",
    "assets/images/flags/w20/de.png",
    "assets/vendor-manifest.json",
)


def _frontend_runtime_files() -> list[Path]:
    patterns = ("*.html", "*.css", "*.js")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(FRONTEND_DIR.rglob(pattern))
    return [
        path
        for path in files
        if "assets/libs" not in path.as_posix()
        and "node_modules" not in path.as_posix()
    ]


def test_primary_pages_use_local_csp() -> None:
    for page_name in PRIMARY_PAGES:
        html = (FRONTEND_DIR / page_name).read_text(encoding="utf-8")
        assert "Content-Security-Policy" in html, page_name
        assert "default-src 'self'" in html, page_name
        assert "script-src 'self'" in html, page_name
        assert "style-src 'self'" in html, page_name
        assert "font-src 'none'" in html, page_name
        assert "img-src 'self' data: blob:" in html, page_name
        for host in FORBIDDEN_RUNTIME_HOSTS:
            assert host not in html, f"{page_name} still references {host}"


def test_frontend_runtime_sources_do_not_reference_remote_cdns() -> None:
    offenders: list[str] = []
    for path in _frontend_runtime_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for host in FORBIDDEN_RUNTIME_HOSTS:
            if host in text:
                rel = path.relative_to(REPO_ROOT).as_posix()
                offenders.append(f"{rel}: {host}")

    assert offenders == []


def test_frontend_local_vendor_assets_are_present() -> None:
    missing_or_empty = [
        asset
        for asset in REQUIRED_LOCAL_ASSETS
        if not (FRONTEND_DIR / asset).is_file()
        or (FRONTEND_DIR / asset).stat().st_size <= 0
    ]

    assert missing_or_empty == []


def test_proxy_table_uses_local_flag_images_before_text_fallback() -> None:
    proxies_js = (FRONTEND_DIR / "assets/js/proxies.js").read_text(encoding="utf-8")

    assert "assets/images/flags/w20/" in proxies_js
    assert "country-flag-text" in proxies_js


def test_vendor_manifest_tracks_local_runtime_assets() -> None:
    manifest = json.loads(
        (FRONTEND_DIR / "assets/vendor-manifest.json").read_text(encoding="utf-8")
    )

    assert "preserve the previous online runtime experience" in manifest["policy"]
    for library in manifest["libraries"]:
        local_path = FRONTEND_DIR / library["local"]
        assert local_path.is_file(), library
        assert local_path.stat().st_size > 0, library
        if "sha256" in library:
            digest = hashlib.sha256(local_path.read_bytes()).hexdigest()
            assert digest == library["sha256"], library

    assert "fonts" not in manifest


def test_frontend_uses_system_fonts_without_binary_font_assets() -> None:
    style = (FRONTEND_DIR / "assets/css/style.css").read_text(encoding="utf-8")

    assert "fonts.css" not in style
    assert "../fonts/" not in style
    assert not (FRONTEND_DIR / "assets/css/fonts.css").exists()
    assert not (FRONTEND_DIR / "assets/fonts").exists()
    assert "--font-rtl-sans" in style
    assert "--font-rtl-display" in style


def test_dompurify_vendor_manifest_matches_bundled_asset() -> None:
    manifest = json.loads(
        (FRONTEND_DIR / "assets/vendor-manifest.json").read_text(encoding="utf-8")
    )
    dompurify = next(
        library for library in manifest["libraries"] if library["name"] == "dompurify"
    )
    purify_js = (FRONTEND_DIR / dompurify["local"]).read_text(encoding="utf-8")

    assert dompurify["version"] == "3.4.10"
    assert f"DOMPurify {dompurify['version']}" in purify_js.splitlines()[0]
    assert f"dompurify@{dompurify['version']}" in dompurify["source"]
