# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for deployed Pages HTTP smoke validation."""

from __future__ import annotations

import json
import threading
import hashlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

from scripts.verify_pages_deployment import verify_pages_deployment


class _StaticHandler(BaseHTTPRequestHandler):
    root: Path

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        rel_path = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        target = (self.root / rel_path).resolve()
        if self.root not in target.parents and target != self.root:
            self.send_response(403)
            self.end_headers()
            return
        if not target.is_file():
            self.send_response(404)
            self.end_headers()
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "content-type",
            (
                "application/json"
                if rel_path.endswith(".json") or rel_path.startswith("api/")
                else "text/html"
            ),
        )
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _write_site(root: Path, *, runtime_config: str | None = None) -> None:
    html = "<!doctype html><html><head><title>ConfigStream</title></head><body>ConfigStream</body></html>"
    for page in (
        "index.html",
        "analytics.html",
        "proxies.html",
        "lab.html",
        "wiki.html",
    ):
        (root / page).write_text(html, encoding="utf-8")
    (root / "assets" / "js").mkdir(parents=True)
    (root / "assets" / "js" / "runtime-config.js").write_text(
        runtime_config
        or 'window.CS_RUNTIME_CONFIG = { PUBLIC_KEY: "public-key", STEGO_KEY: "stego-key" };\n',
        encoding="utf-8",
    )
    (root / "assets" / "js" / "constants.js").write_text(
        "window.CS_CONSTANTS = {};\n",
        encoding="utf-8",
    )
    (root / "assets" / "js" / "stego.js").write_text(
        "window.CS_STEGO = {};\n",
        encoding="utf-8",
    )
    metadata = {"proxies_snapshot_hash": "a" * 64}
    proxies: list[object] = []
    (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (root / "proxies.json").write_text(json.dumps(proxies), encoding="utf-8")
    (root / "health.json").write_text(
        json.dumps(
            {
                "status": "degraded",
                "run_id": "12345",
                "source_commit": "a" * 40,
            }
        ),
        encoding="utf-8",
    )
    (root / "base64.txt").write_text("", encoding="utf-8")
    (root / "chosen").mkdir()
    (root / "chosen" / "base64.txt").write_text("", encoding="utf-8")
    (root / "api").mkdir()
    (root / "api" / "stats").write_text(json.dumps(metadata), encoding="utf-8")
    (root / "api" / "proxies").write_text(json.dumps(proxies), encoding="utf-8")
    files: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        rel_path = path.relative_to(root).as_posix()
        files.append(
            {
                "path": rel_path,
                "size_bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "category": "control",
            }
        )
    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_generated_at": datetime.now(timezone.utc).isoformat(),
        "trace_id": "trace",
        "source_commit": "a" * 40,
        "run_id": "12345",
        "run_attempt": "1",
        "file_count": len(files),
        "total_size_bytes": sum(cast(int, item["size_bytes"]) for item in files),
        "files": files,
    }
    (root / "artifact_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )


def _serve(root: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = type("StaticHandler", (_StaticHandler,), {"root": root.resolve()})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host_value = server.server_address[0]
    host = (
        host_value.decode("utf-8")
        if isinstance(host_value, bytes)
        else str(host_value)
    )
    port = int(server.server_address[1])
    return server, f"http://{host}:{port}/"


def test_verify_pages_deployment_accepts_valid_site(tmp_path: Path) -> None:
    _write_site(tmp_path)
    server, url = _serve(tmp_path)
    try:
        assert verify_pages_deployment(url, timeout=5.0) == []
    finally:
        server.shutdown()
        server.server_close()


def test_verify_pages_deployment_rejects_runtime_placeholder(tmp_path: Path) -> None:
    _write_site(
        tmp_path,
        runtime_config='window.CS_RUNTIME_CONFIG = { PUBLIC_KEY: "PLACEHOLDER_PUBLIC_KEY", STEGO_KEY: "stego-key" };\n',
    )
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(url, timeout=5.0)
    finally:
        server.shutdown()
        server.server_close()

    assert any("placeholder marker" in error for error in errors)


def test_verify_pages_deployment_rejects_api_alias_drift(tmp_path: Path) -> None:
    _write_site(tmp_path)
    (tmp_path / "api" / "stats").write_text(
        json.dumps({"proxies_snapshot_hash": "b" * 64}),
        encoding="utf-8",
    )
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(url, timeout=5.0)
    finally:
        server.shutdown()
        server.server_close()

    assert "api/stats does not match metadata.json" in errors


def test_verify_pages_deployment_rejects_manifest_hash_drift(
    tmp_path: Path,
) -> None:
    _write_site(tmp_path)
    (tmp_path / "base64.txt").write_text("changed after manifest", encoding="utf-8")
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(url, timeout=5.0)
    finally:
        server.shutdown()
        server.server_close()

    assert "artifact_manifest.json sha256 mismatch: base64.txt" in errors


def test_verify_pages_deployment_requires_health_run_identity(
    tmp_path: Path,
) -> None:
    _write_site(tmp_path)
    (tmp_path / "health.json").write_text(
        json.dumps({"status": "degraded"}),
        encoding="utf-8",
    )
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(url, timeout=5.0)
    finally:
        server.shutdown()
        server.server_close()

    assert "health.json missing run_id or source_commit" in errors
