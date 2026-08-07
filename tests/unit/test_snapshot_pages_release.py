# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from configstream.signer import Signer
from scripts import snapshot_pages_release


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def _serve(root: Path):
    def handler(*args, **kwargs):
        return _QuietHandler(*args, directory=str(root), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _build_site(
    root: Path,
    *,
    signer: Signer | None = None,
    status: str = "ok",
    generated_at: datetime | None = None,
) -> dict[str, bytes]:
    root.mkdir()
    timestamp = (generated_at or datetime.now(timezone.utc)).isoformat()
    payloads = {
        "index.html": b"<html>ConfigStream</html>",
        "metadata.json": json.dumps(
            {
                "generated_at": timestamp,
                "last_updated_utc": timestamp,
                "update_interval_hours": 4,
                "total_working": 1,
                "source_commit": "a" * 40,
            },
            sort_keys=True,
        ).encode(),
        "health.json": json.dumps(
            {
                "status": status,
                "total_working": 1,
                "schema_validated": True,
                "source_commit": "a" * 40,
            },
            sort_keys=True,
        ).encode(),
    }
    for name, body in payloads.items():
        (root / name).write_bytes(body)
    files = [
        {
            "path": name,
            "size_bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
        for name, body in sorted(payloads.items())
    ]
    manifest: dict[str, object] = {
        "source_commit": "a" * 40,
        "release_id": "test-release",
        "files": files,
    }
    if signer is not None:
        manifest["manifest_signature"] = signer.sign_manifest(manifest)
    manifest_body = json.dumps(manifest, sort_keys=True).encode()
    (root / "artifact_manifest.json").write_bytes(manifest_body)
    payloads["artifact_manifest.json"] = manifest_body
    return payloads


def _remote_fetcher(payloads: dict[str, bytes]):
    def fetch(url: str, timeout: float, pins=None) -> bytes:
        del timeout, pins
        name = url.rstrip("/").rsplit("/", 1)[-1]
        return payloads[name]

    return fetch


def test_snapshot_downloads_hash_verified_local_release(tmp_path: Path) -> None:
    site = tmp_path / "site"
    _build_site(site)
    server, thread = _serve(site)
    destination = tmp_path / "snapshot"
    try:
        report = snapshot_pages_release.snapshot(
            f"http://127.0.0.1:{server.server_port}/", destination
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert (destination / "index.html").read_text(encoding="utf-8") == "<html>ConfigStream</html>"
    assert (destination / "artifact_manifest.json").is_file()
    assert report["source_commit"] == "a" * 40
    assert report["file_count"] == 3
    assert report["health_status"] == "ok"
    assert report["manifest_signature_verified"] is False
    assert report["local_source"] is True


def test_snapshot_rejects_manifest_hash_mismatch(tmp_path: Path) -> None:
    site = tmp_path / "site"
    _build_site(site)
    manifest_path = site / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    server, thread = _serve(site)
    try:
        with pytest.raises(ValueError, match="hash mismatch"):
            snapshot_pages_release.snapshot(
                f"http://127.0.0.1:{server.server_port}/", tmp_path / "snapshot"
            )
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_snapshot_rejects_degraded_release(tmp_path: Path) -> None:
    site = tmp_path / "site"
    _build_site(site, status="degraded")
    server, thread = _serve(site)
    try:
        with pytest.raises(ValueError, match="health is degraded"):
            snapshot_pages_release.snapshot(
                f"http://127.0.0.1:{server.server_port}/", tmp_path / "snapshot"
            )
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_snapshot_rejects_stale_release(tmp_path: Path) -> None:
    site = tmp_path / "site"
    _build_site(site, generated_at=datetime.now(timezone.utc) - timedelta(hours=13))
    server, thread = _serve(site)
    try:
        with pytest.raises(ValueError, match="metadata is stale"):
            snapshot_pages_release.snapshot(
                f"http://127.0.0.1:{server.server_port}/", tmp_path / "snapshot"
            )
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_public_snapshot_requires_https() -> None:
    with pytest.raises(ValueError, match="require HTTPS"):
        snapshot_pages_release.snapshot("http://example.com/", Path("unused"))


def test_snapshot_rejects_cross_origin_redirect() -> None:
    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:9/private")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(ValueError, match="crossed the trusted origin"):
            snapshot_pages_release._fetch(
                f"http://127.0.0.1:{server.server_port}/artifact_manifest.json",
                2,
            )
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    "candidate_url",
    ["https://example.com/?candidate=1", "https://example.com/#ignored"],
)
def test_snapshot_rejects_base_url_query_or_fragment(candidate_url: str) -> None:
    with pytest.raises(ValueError, match="must not contain a query or fragment"):
        snapshot_pages_release.snapshot(candidate_url, Path("unused"))


def test_snapshot_recovers_interrupted_directory_swap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    destination = tmp_path / "snapshot"
    backup = tmp_path / "snapshot.replaced"
    backup.mkdir()
    (backup / "last-known-good.txt").write_text("verified", encoding="utf-8")

    def fail_fetch(*args, **kwargs):
        del args, kwargs
        raise ValueError("offline")

    monkeypatch.setattr(snapshot_pages_release, "_fetch", fail_fetch)

    with pytest.raises(ValueError, match="offline"):
        snapshot_pages_release.snapshot(
            "https://example.com/", destination, public_key="11" * 32
        )

    assert (destination / "last-known-good.txt").read_text(encoding="utf-8") == "verified"
    assert not backup.exists()


@pytest.mark.parametrize("value", ["asset.json?download=1", "asset.json#fragment"])
def test_snapshot_rejects_manifest_paths_with_url_components(value: str) -> None:
    with pytest.raises(ValueError, match="unsafe manifest path"):
        snapshot_pages_release._safe_relative(value)


def test_public_snapshot_requires_configured_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    site = tmp_path / "site"
    payloads = _build_site(site)
    monkeypatch.setattr(snapshot_pages_release, "_fetch", _remote_fetcher(payloads))
    with pytest.raises(ValueError, match="configured CS_PUBLIC_KEY"):
        snapshot_pages_release.snapshot("https://example.com/", tmp_path / "snapshot", public_key="")


def test_public_snapshot_verifies_signature(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    signer = Signer("11" * 32)
    site = tmp_path / "site"
    payloads = _build_site(site, signer=signer)
    monkeypatch.setattr(snapshot_pages_release, "_fetch", _remote_fetcher(payloads))

    report = snapshot_pages_release.snapshot(
        "https://example.com/",
        tmp_path / "snapshot",
        public_key=signer.get_public_key_hex(),
    )

    assert report["manifest_signature_verified"] is True
    assert report["local_source"] is False


def test_public_snapshot_rejects_invalid_signature(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    signer = Signer("11" * 32)
    site = tmp_path / "site"
    payloads = _build_site(site, signer=signer)
    manifest = json.loads(payloads["artifact_manifest.json"])
    manifest["source_commit"] = "b" * 40
    payloads["artifact_manifest.json"] = json.dumps(manifest, sort_keys=True).encode()
    monkeypatch.setattr(snapshot_pages_release, "_fetch", _remote_fetcher(payloads))

    with pytest.raises(ValueError, match="signature is invalid or stale"):
        snapshot_pages_release.snapshot(
            "https://example.com/",
            tmp_path / "snapshot",
            public_key=signer.get_public_key_hex(),
        )


def test_snapshot_rejects_private_dns_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        snapshot_pages_release.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("10.0.0.8", 443))],
    )
    parsed = snapshot_pages_release.urllib.parse.urlparse("https://example.com/")
    with pytest.raises(ValueError, match="non-global"):
        snapshot_pages_release._resolve_and_pin(parsed, {})


def test_local_snapshot_requires_loopback_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        snapshot_pages_release.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("10.0.0.8", 80))],
    )
    parsed = snapshot_pages_release.urllib.parse.urlparse("http://test.localhost/")
    with pytest.raises(ValueError, match="outside loopback"):
        snapshot_pages_release._resolve_and_pin(parsed, {})


def test_snapshot_rejects_dns_rebinding(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["93.184.216.34", "1.1.1.1"])
    monkeypatch.setattr(
        snapshot_pages_release.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", (next(answers), 443))],
    )
    parsed = snapshot_pages_release.urllib.parse.urlparse("https://example.com/")
    pins: dict[str, set[str]] = {}
    assert snapshot_pages_release._resolve_and_pin(parsed, pins) == {"93.184.216.34"}
    with pytest.raises(ValueError, match="rebinding"):
        snapshot_pages_release._resolve_and_pin(parsed, pins)
