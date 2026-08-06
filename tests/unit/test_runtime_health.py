# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from configstream.runtime_health import evaluate_runtime_health


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _build_artifact(root: Path, *, generated_at: datetime, total_working: int = 2) -> None:
    root.mkdir(parents=True, exist_ok=True)
    generated = generated_at.isoformat()
    _write_json(
        root / "metadata.json",
        {
            "generated_at": generated,
            "last_updated_utc": generated,
            "total_working": total_working,
            "update_interval_hours": 4,
        },
    )
    _write_json(
        root / "health.json",
        {
            "status": "ok" if total_working else "degraded",
            "generated_at": generated,
            "total_working": total_working,
            "schema_validated": True,
            "native_clients_validated": True,
            "release_blockers": [],
        },
    )
    _write_json(root / "proxies.json", [{"id": "p1"}] if total_working else [])
    files = []
    for name in ("health.json", "metadata.json", "proxies.json"):
        content = (root / name).read_bytes()
        files.append(
            {
                "path": name,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    _write_json(root / "artifact_manifest.json", {"files": files})


def test_runtime_health_accepts_fresh_valid_artifact(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    _build_artifact(tmp_path, generated_at=now - timedelta(minutes=5))

    result = evaluate_runtime_health(tmp_path, now=now, max_age_hours=12)

    assert result.ready is True
    assert result.status == "healthy"
    assert result.reasons == ()
    assert result.files_present >= 4


def test_runtime_health_rejects_stale_artifact(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    _build_artifact(tmp_path, generated_at=now - timedelta(hours=13))

    result = evaluate_runtime_health(tmp_path, now=now, max_age_hours=12)

    assert result.ready is False
    assert result.status == "unhealthy"
    assert any(reason.startswith("artifact_stale:") for reason in result.reasons)


def test_runtime_health_rejects_manifest_hash_mismatch(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    _build_artifact(tmp_path, generated_at=now)
    (tmp_path / "proxies.json").write_text("[]", encoding="utf-8")

    result = evaluate_runtime_health(tmp_path, now=now, max_age_hours=12)

    assert result.ready is False
    assert "manifest_hash_mismatch:proxies.json" in result.reasons


def test_runtime_health_rejects_degraded_zero_output(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    _build_artifact(tmp_path, generated_at=now, total_working=0)

    result = evaluate_runtime_health(tmp_path, now=now, max_age_hours=12)

    assert result.ready is False
    assert "no_working_proxies" in result.reasons
    assert "public_health_degraded" in result.reasons


def test_runtime_health_rejects_non_schema_healthy_alias(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    _build_artifact(tmp_path, generated_at=now)
    health_path = tmp_path / "health.json"
    health = json.loads(health_path.read_text(encoding="utf-8"))
    health["status"] = "healthy"
    _write_json(health_path, health)
    manifest_path = tmp_path / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    health_entry = next(item for item in manifest["files"] if item["path"] == "health.json")
    body = health_path.read_bytes()
    health_entry["size_bytes"] = len(body)
    health_entry["sha256"] = hashlib.sha256(body).hexdigest()
    _write_json(manifest_path, manifest)

    result = evaluate_runtime_health(tmp_path, now=now, max_age_hours=12)

    assert result.ready is False
    assert "public_health_degraded" in result.reasons


def test_runtime_health_requires_explicit_schema_validation(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    _build_artifact(tmp_path, generated_at=now)
    health_path = tmp_path / "health.json"
    health = json.loads(health_path.read_text(encoding="utf-8"))
    health.pop("schema_validated")
    _write_json(health_path, health)
    manifest_path = tmp_path / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    health_entry = next(item for item in manifest["files"] if item["path"] == "health.json")
    body = health_path.read_bytes()
    health_entry["size_bytes"] = len(body)
    health_entry["sha256"] = hashlib.sha256(body).hexdigest()
    _write_json(manifest_path, manifest)

    result = evaluate_runtime_health(tmp_path, now=now, max_age_hours=12)

    assert result.ready is False
    assert "schema_not_validated" in result.reasons


def test_runtime_health_rejects_duplicate_manifest_paths(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    _build_artifact(tmp_path, generated_at=now)
    manifest_path = tmp_path / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].append(dict(manifest["files"][0]))
    _write_json(manifest_path, manifest)

    result = evaluate_runtime_health(tmp_path, now=now, max_age_hours=12)

    assert result.ready is False
    assert "manifest_duplicate_path:health.json" in result.reasons
