# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for deployed Pages HTTP smoke validation."""

from __future__ import annotations

import json
import threading
import hashlib
import urllib.error
from unittest.mock import patch
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

from scripts.verify_pages_deployment import (
    _fetch,
    evaluate_candidate_match,
    main,
    verify_pages_deployment,
)
from configstream.signer import Signer


class _StaticHandler(BaseHTTPRequestHandler):
    root: Path
    last_headers: dict[str, str] = {}

    def do_GET(self) -> None:
        _StaticHandler.last_headers = {k.lower(): v for k, v in self.headers.items()}
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


def _write_site(
    root: Path,
    *,
    runtime_config: str | None = None,
    source_commit: str = "a" * 40,
    run_id: str = "12345",
    manifest_digest: str | None = None,
    signer: Signer | None = None,
) -> None:
    html = "<!doctype html><html><head><title>ConfigStream</title></head><body>ConfigStream</body></html>"
    for page in (
        "index.html",
        "analytics.html",
        "proxies.html",
        "lab.html",
        "wiki.html",
    ):
        (root / page).write_text(html, encoding="utf-8")
    (root / "assets" / "js").mkdir(parents=True, exist_ok=True)
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
                "run_id": run_id,
                "source_commit": source_commit,
            }
        ),
        encoding="utf-8",
    )
    (root / "pipeline_events.jsonl").write_text(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "pipeline_complete",
                "message": "Generated degraded artifact set.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "base64.txt").write_text("", encoding="utf-8")
    (root / "chosen").mkdir(exist_ok=True)
    (root / "chosen" / "base64.txt").write_text("", encoding="utf-8")
    (root / "api").mkdir(exist_ok=True)
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
        "source_commit": source_commit,
        "run_id": run_id,
        "run_attempt": "1",
        "file_count": len(files),
        "total_size_bytes": sum(cast(int, item["size_bytes"]) for item in files),
        "files": files,
    }
    if manifest_digest is not None:
        manifest["digest"] = manifest_digest
    if signer is not None:
        sig = signer.sign_manifest(manifest)
        manifest["manifest_signature"] = sig
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
        host_value.decode("utf-8") if isinstance(host_value, bytes) else str(host_value)
    )
    port = int(server.server_address[1])
    return server, f"http://{host}:{port}/"


def test_candidate_identity_matching_logic() -> None:
    live_manifest = {
        "commit_sha": "abc1234",
        "workflow_run_id": "999888",
        "digest": "sha256-xyz",
    }

    # Exact match passes
    assert evaluate_candidate_match(live_manifest, "abc1234", "999888", "sha256-xyz") is True

    # Stale SHA fails
    assert evaluate_candidate_match(live_manifest, "old1111", "999888", "sha256-xyz") is False

    # Stale run ID fails
    assert evaluate_candidate_match(live_manifest, "abc1234", "888777", "sha256-xyz") is False

    # Digest mismatch fails
    assert evaluate_candidate_match(live_manifest, "abc1234", "999888", "sha256-other") is False

    # None / omitted candidate checks pass
    assert evaluate_candidate_match(live_manifest, None, None, None) is True
    assert evaluate_candidate_match(live_manifest, "abc1234", None, None) is True

    # Fallback field names (source_commit, run_id, sha256)
    alt_manifest = {
        "source_commit": "def5678",
        "run_id": "555444",
        "sha256": "digest-123",
    }
    assert evaluate_candidate_match(alt_manifest, "def5678", "555444", "digest-123") is True
    assert evaluate_candidate_match(alt_manifest, "def5678", "wrong", "digest-123") is False

    # Non-dict manifest fails
    assert evaluate_candidate_match("not-a-dict", "abc1234", "999888", "sha256-xyz") is False


def test_verify_pages_deployment_accepts_valid_site(tmp_path: Path) -> None:
    _write_site(tmp_path)
    server, url = _serve(tmp_path)
    try:
        assert verify_pages_deployment(url, timeout=5.0) == []
    finally:
        server.shutdown()
        server.server_close()


def test_verify_pages_deployment_candidate_exact_match(tmp_path: Path) -> None:
    commit = "a" * 40
    run_id = "12345"
    _write_site(tmp_path, source_commit=commit, run_id=run_id)
    digest = hashlib.sha256((tmp_path / "artifact_manifest.json").read_bytes()).hexdigest()
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(
            url,
            timeout=5.0,
            expected_commit=commit,
            expected_run_id=run_id,
            expected_digest=digest,
        )
        assert errors == []
    finally:
        server.shutdown()
        server.server_close()


def test_verify_pages_deployment_candidate_commit_mismatch(tmp_path: Path) -> None:
    _write_site(tmp_path, source_commit="a" * 40, run_id="12345")
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(
            url,
            timeout=5.0,
            expected_commit="b" * 40,
        )
        assert any("commit mismatch" in e or "candidate identity mismatch" in e for e in errors)
    finally:
        server.shutdown()
        server.server_close()


def test_verify_pages_deployment_candidate_run_id_mismatch(tmp_path: Path) -> None:
    _write_site(tmp_path, source_commit="a" * 40, run_id="12345")
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(
            url,
            timeout=5.0,
            expected_run_id="99999",
        )
        assert any("run_id mismatch" in e or "candidate identity mismatch" in e for e in errors)
    finally:
        server.shutdown()
        server.server_close()


def test_verify_pages_deployment_candidate_digest_mismatch(tmp_path: Path) -> None:
    _write_site(tmp_path, source_commit="a" * 40, run_id="12345")
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(
            url,
            timeout=5.0,
            expected_digest="digest-wrong",
        )
        assert any("digest mismatch" in e or "candidate identity mismatch" in e for e in errors)
    finally:
        server.shutdown()
        server.server_close()


def test_verify_pages_deployment_fetches_with_cache_busting_headers(tmp_path: Path) -> None:
    _write_site(tmp_path)
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(url, timeout=5.0)
        assert errors == []
        assert _StaticHandler.last_headers.get("cache-control") == "no-cache, no-store"
    finally:
        server.shutdown()
        server.server_close()


def test_fetch_returns_transport_failure_response() -> None:
    """A connection failure is reportable validation evidence, not a crash."""
    with patch("urllib.request.OpenerDirector.open", side_effect=urllib.error.URLError("offline")):
        response = _fetch("https://example.invalid/", timeout=0.1)
    assert response.status == 0
    assert response.body == b""


def test_verify_pages_deployment_signature_gate_passes_valid(tmp_path: Path) -> None:
    signer = Signer(private_key_hex="11" * 32)
    pub_hex = signer.get_public_key_hex()
    _write_site(tmp_path, signer=signer)
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(url, timeout=5.0, public_key=pub_hex)
        assert errors == []
    finally:
        server.shutdown()
        server.server_close()


def test_verify_pages_deployment_signature_gate_fails_tampered_or_missing(tmp_path: Path) -> None:
    signer = Signer(private_key_hex="11" * 32)
    pub_hex = signer.get_public_key_hex()

    # Case 1: Missing signature when public_key required
    _write_site(tmp_path)
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(url, timeout=5.0, public_key=pub_hex)
        assert any("signature" in e.lower() for e in errors)
    finally:
        server.shutdown()
        server.server_close()

    # Case 2: Tampered signature
    _write_site(tmp_path, signer=signer)
    manifest_path = tmp_path / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest_signature"]["signature"] = "ff" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    server2, url2 = _serve(tmp_path)
    try:
        errors2 = verify_pages_deployment(url2, timeout=5.0, public_key=pub_hex)
        assert any("signature" in e.lower() for e in errors2)
    finally:
        server2.shutdown()
        server2.server_close()


def test_main_cli_candidate_matching_and_report_json(tmp_path: Path) -> None:
    _write_site(tmp_path, source_commit="a" * 40, run_id="12345")
    digest = hashlib.sha256((tmp_path / "artifact_manifest.json").read_bytes()).hexdigest()
    server, url = _serve(tmp_path)
    report_file = tmp_path / "report.json"
    try:
        # Match passes
        rc = main([
            url,
            "--expected-commit", "a" * 40,
            "--expected-run-id", "12345",
            "--expected-digest", digest,
            "--report-file", str(report_file),
        ])
        assert rc == 0
        report = json.loads(report_file.read_text(encoding="utf-8"))
        assert report["status"] == "passed"
        assert report["errors"] == []

        # Mismatch fails with code 1 and writes structured JSON errors
        rc_mismatch = main([
            url,
            "--expected-commit", "wrong-commit",
            "--report-file", str(report_file),
        ])
        assert rc_mismatch == 1
        report_fail = json.loads(report_file.read_text(encoding="utf-8"))
        assert report_fail["status"] == "failed"
        assert len(report_fail["errors"]) > 0
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


def test_verify_pages_deployment_rejects_invalid_pipeline_events(
    tmp_path: Path,
) -> None:
    _write_site(tmp_path)
    (tmp_path / "pipeline_events.jsonl").write_text(
        '{"timestamp":"not-a-date","event_type":"error","message":"Bearer secret"}\n',
        encoding="utf-8",
    )
    server, url = _serve(tmp_path)
    try:
        errors = verify_pages_deployment(url, timeout=5.0)
    finally:
        server.shutdown()
        server.server_close()

    assert any(
        "pipeline_events.jsonl line 1 contains forbidden marker" in error
        for error in errors
    )
    assert "artifact_manifest.json sha256 mismatch: pipeline_events.jsonl" in errors
