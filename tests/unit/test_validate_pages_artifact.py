# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for GitHub Pages artifact validation."""

from __future__ import annotations

import json
import hashlib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.validate_pages_artifact import (
    REQUIRED_EXISTS,
    REQUIRED_NONEMPTY,
    validate_pages_artifact,
    write_pages_contract,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("proxies.txt", "ok")


def _singbox_payload() -> dict:
    return {
        "outbounds": [
            {"type": "selector", "tag": "Proxy", "outbounds": ["Auto", "direct"]},
            {"type": "urltest", "tag": "Auto", "outbounds": ["direct"]},
            {"type": "direct", "tag": "direct"},
        ]
    }


def _clash_payload() -> str:
    return "\n".join(
        [
            "port: 7890",
            "proxies: []",
            "proxy-groups:",
            "  - name: PROXY",
            "    type: select",
            "    proxies:",
            "      - DIRECT",
            "rules:",
            "  - MATCH,PROXY",
            "",
        ]
    )


def _metadata_payload() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    audit = {
        "trace_id": "-",
        "tested": 0,
        "working": 0,
        "total_revived": 0,
        "revived_warp": 0,
        "revived_vwarp": 0,
        "revival_attempts": 0,
        "revival_win_rate": 0.0,
        "fetched_sources": 0,
        "total_sources": 0,
        "source_toxicity_rate": 0.0,
        "backpressure_drop": 0,
        "time_limited": False,
    }
    return {
        "schema_version": "3.0.2",
        "version": "3.0.2",
        "generated_at": now,
        "last_updated_utc": now,
        "trace_id": "-",
        "proxies_snapshot_hash": "a" * 64,
        "previous_proxies_snapshot_hash": None,
        "total_lines_sourced": 0,
        "total_unique_candidates": 0,
        "total_valid_proxies": 0,
        "total_proxies": 0,
        "total_tested": 0,
        "total_working": 0,
        "success_rate": 0.0,
        "latency_distribution": {
            "fast": 0,
            "medium": 0,
            "slow": 0,
            "very_slow": 0,
        },
        "protocols": {},
        "country_stats": {},
        "drop_reasons": {},
        "rejection_reasons": {},
        "asns": {},
        "total_revived": 0,
        "total_clean": 0,
        "total_smart_chains": 0,
        "smart_chain_count": 0,
        "chain_outbounds_count": 0,
        "backpressure_drop": 0,
        "revived_warp": 0,
        "revived_vwarp": 0,
        "warp_attempts": 0,
        "vwarp_attempts": 0,
        "vwarp_success": 0,
        "vwarp_win_rate": 0.0,
        "washing_enabled": False,
        "shielded_count": 0,
        "shielded_candidate_count": 0,
        "shielded_verified_count": 0,
        "evasion_utls_enabled": 0,
        "evasion_alpn_enabled": 0,
        "evasion_fragmentation_enabled": 0,
        "evasion_multiplexing_enabled": 0,
        "evasion_dns_safe_count": 0,
        "evasion_dns_hardened_count": 0,
        "duration_seconds": 0.0,
        "geo_resolved": 0,
        "cache_misses": 0,
        "final_count": 0,
        "time_limited": False,
        "time_limit_seconds": 0,
        "total_configured_sources": 0,
        "fetched_sources": 0,
        "sources_count": 0,
        "total_sources": 0,
        "update_interval_hours": 4,
        "latency_by_country": {},
        "latency_by_protocol": {},
        "chosen_subset_size": 0,
        "pipeline_execution_audit": audit,
    }


def _write_manifest(root: Path) -> None:
    now = datetime.now(timezone.utc).isoformat()
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        rel_path = path.relative_to(root).as_posix()
        files.append(
            {
                "path": rel_path,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "category": "control" if rel_path.endswith(".json") else "subscription",
            }
        )
    manifest = {
        "schema_version": "1.0",
        "generated_at": now,
        "artifact_generated_at": now,
        "trace_id": "-",
        "source_commit": "",
        "run_id": "",
        "run_attempt": "",
        "file_count": len(files),
        "total_size_bytes": sum(item["size_bytes"] for item in files),
        "files": files,
    }
    _write_text(root / "artifact_manifest.json", json.dumps(manifest))


def _write_valid_artifact(root: Path) -> None:
    metadata_payload = _metadata_payload()
    for rel_path in REQUIRED_EXISTS:
        if rel_path == "artifact_manifest.json":
            continue
        path = root / rel_path
        if rel_path.endswith(".zip"):
            _write_zip(path)
        elif rel_path == "health.json":
            now = datetime.now(timezone.utc).isoformat()
            _write_text(
                path,
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "status": "degraded",
                        "generated_at": now,
                        "trace_id": "-",
                        "source_commit": "",
                        "run_id": "",
                        "run_attempt": "",
                        "total_working": 0,
                        "total_tested": 0,
                        "schema_validated": False,
                        "notes": [],
                    }
                ),
            )
        elif rel_path == "metadata.json" or rel_path == "api/stats":
            _write_text(path, json.dumps(metadata_payload))
        elif rel_path.endswith("proxies.json") or rel_path == "api/proxies":
            _write_text(path, "[]")
        elif rel_path.startswith("singbox") and rel_path.endswith(".json"):
            _write_text(path, json.dumps(_singbox_payload()))
        elif rel_path.startswith("clash") and rel_path.endswith(".yaml"):
            _write_text(path, _clash_payload())
        elif rel_path.endswith(".json"):
            _write_text(path, "{}")
        else:
            _write_text(path)
    _write_manifest(root)


def _write_manifest_without_metadata(root: Path) -> None:
    _write_manifest(root)
    manifest = json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))
    manifest["files"] = [
        item for item in manifest["files"] if item.get("path") != "metadata.json"
    ]
    manifest["file_count"] = len(manifest["files"])
    manifest["total_size_bytes"] = sum(item["size_bytes"] for item in manifest["files"])
    _write_text(root / "artifact_manifest.json", json.dumps(manifest))


def test_validate_pages_artifact_accepts_complete_artifact(tmp_path: Path) -> None:
    _write_valid_artifact(tmp_path)

    assert validate_pages_artifact(tmp_path) == []


def test_validate_pages_artifact_reports_missing_and_empty_files(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    missing_rel = REQUIRED_EXISTS[0]
    empty_rel = next(path for path in REQUIRED_NONEMPTY if path != missing_rel)
    (tmp_path / missing_rel).unlink()
    _write_text(tmp_path / empty_rel, "")

    errors = validate_pages_artifact(tmp_path)

    assert any("missing required file" in error for error in errors)
    assert any("required file is empty" in error for error in errors)


def test_validate_pages_artifact_reports_invalid_json(tmp_path: Path) -> None:
    _write_valid_artifact(tmp_path)
    _write_text(tmp_path / "metadata.json", "{")

    errors = validate_pages_artifact(tmp_path)

    assert any("invalid JSON in metadata.json" in error for error in errors)


def test_validate_pages_artifact_reports_invalid_zip(tmp_path: Path) -> None:
    _write_valid_artifact(tmp_path)
    _write_text(tmp_path / "side_products.zip", "not a zip")

    errors = validate_pages_artifact(tmp_path)

    assert any("invalid ZIP in side_products.zip" in error for error in errors)


def test_validate_pages_artifact_requires_side_product_proxy_member(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    with zipfile.ZipFile(tmp_path / "side_products.zip", "w") as archive:
        archive.writestr("README.txt", "ok")

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "side_products.zip missing ZIP member: proxies.txt" in error for error in errors
    )


def test_validate_pages_artifact_rejects_unsafe_zip_member_path(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    with zipfile.ZipFile(tmp_path / "side_products.zip", "w") as archive:
        archive.writestr("proxies.txt", "ok")
        archive.writestr("../escape.txt", "bad")

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "side_products.zip contains unsafe ZIP member path: ../escape.txt" in error
        for error in errors
    )


def test_validate_pages_artifact_rejects_deploy_secret_in_zip_member(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    with zipfile.ZipFile(tmp_path / "side_products.zip", "w") as archive:
        archive.writestr("proxies.txt", "ok")
        archive.writestr("openvpn/client.ovpn", "ADMIN_API_KEY=super-secret-value\n")

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "side_products.zip ZIP member leaks deploy secret assignment: openvpn/client.ovpn"
        in error
        for error in errors
    )


def test_validate_pages_artifact_allows_proxy_credentials_in_zip_member(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    with zipfile.ZipFile(tmp_path / "side_products.zip", "w") as archive:
        archive.writestr("proxies.txt", "ss://method:proxy-password@example.com:443")
        archive.writestr(
            "wireguard/client.conf",
            "[Interface]\nPrivateKey = proxy-private-key\n",
        )

    errors = validate_pages_artifact(tmp_path)

    assert not any("ZIP member leaks deploy secret" in error for error in errors)


def test_validate_pages_artifact_requires_manifest_entries(tmp_path: Path) -> None:
    _write_valid_artifact(tmp_path)
    _write_manifest_without_metadata(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "artifact_manifest.json missing file entry: metadata.json" in error
        for error in errors
    )


def test_validate_pages_artifact_rejects_unknown_health_status(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    _write_text(tmp_path / "health.json", json.dumps({"status": "unknown"}))

    errors = validate_pages_artifact(tmp_path)

    assert any("health.json status" in error for error in errors)


def test_validate_pages_artifact_reports_manifest_hash_mismatch(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    _write_text(tmp_path / "base64.txt", "changed")

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "artifact_manifest.json sha256 mismatch: base64.txt" in error
        for error in errors
    )


def test_validate_pages_artifact_reports_missing_metadata_schema_key(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    metadata = _metadata_payload()
    metadata.pop("total_working")
    _write_text(tmp_path / "metadata.json", json.dumps(metadata))
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "metadata.json missing required key from schema: total_working" in error
        for error in errors
    )


def test_validate_pages_artifact_reports_unknown_metadata_schema_key(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    metadata = _metadata_payload()
    metadata["legacy_extra"] = True
    _write_text(tmp_path / "metadata.json", json.dumps(metadata))
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "metadata.json contains unknown schema key: legacy_extra" in error
        for error in errors
    )


def test_validate_pages_artifact_reports_nested_metadata_schema_drift(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    metadata = _metadata_payload()
    metadata["latency_distribution"].pop("fast")
    metadata["pipeline_execution_audit"]["unexpected"] = 1
    _write_text(tmp_path / "metadata.json", json.dumps(metadata))
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "metadata.json latency_distribution missing required key: fast" in error
        for error in errors
    )
    assert any(
        "metadata.json pipeline_execution_audit contains unknown schema key: unexpected"
        in error
        for error in errors
    )


def test_validate_pages_artifact_reports_protocol_detail_schema_drift(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    proxy = {
        "config": "vless://11111111-1111-4111-8111-111111111111@example.com:443",
        "protocol": "vless",
        "address": "example.com",
        "port": 443,
        "uuid": "11111111-1111-4111-8111-111111111111",
        "process": "native",
        "details": {
            "uuid": "not-a-uuid-v4",
            "flow": "",
            "type": "ws",
            "security": "tls",
            "unexpected": True,
        },
    }
    _write_text(tmp_path / "proxies.json", json.dumps([proxy]))
    _write_text(tmp_path / "api" / "proxies", json.dumps([proxy]))
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "proxies.json[0].details.uuid does not match required pattern" in error
        for error in errors
    )
    assert any(
        "proxies.json[0].details contains unknown schema key: unexpected" in error
        for error in errors
    )


def test_validate_pages_artifact_reports_api_alias_drift(tmp_path: Path) -> None:
    _write_valid_artifact(tmp_path)
    _write_text(tmp_path / "api" / "proxies", '[{"config":"drift"}]')
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any("api/proxies must match proxies.json" in error for error in errors)


def test_validate_pages_artifact_reports_singbox_unknown_outbound_reference(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    payload = _singbox_payload()
    payload["outbounds"][0]["outbounds"] = ["missing"]
    _write_text(tmp_path / "singbox.json", json.dumps(payload))
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "singbox.json unknown outbound reference: missing" in error for error in errors
    )


def test_validate_pages_artifact_reports_singbox_unknown_detour(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    payload = _singbox_payload()
    payload["outbounds"].append(
        {"type": "vless", "tag": "relay", "server": "example.com", "detour": "missing"}
    )
    _write_text(tmp_path / "singbox.json", json.dumps(payload))
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "singbox.json unknown outbound detour: missing" in error for error in errors
    )


def test_validate_pages_artifact_reports_singbox_unknown_route_outbound(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    payload = _singbox_payload()
    payload["route"] = {"rules": [{"domain": ["example.com"], "outbound": "missing"}]}
    _write_text(tmp_path / "singbox.json", json.dumps(payload))
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "singbox.json unknown route outbound: missing" in error for error in errors
    )


def test_validate_pages_artifact_reports_singbox_unknown_dns_detour(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    payload = _singbox_payload()
    payload["dns"] = {
        "servers": [{"tag": "remote", "address": "tls://1.1.1.1", "detour": "missing"}]
    }
    _write_text(tmp_path / "singbox.json", json.dumps(payload))
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any("singbox.json unknown DNS detour: missing" in error for error in errors)


def test_validate_pages_artifact_reports_clash_unknown_group_reference(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    _write_text(
        tmp_path / "clash.yaml",
        "\n".join(
            [
                "port: 7890",
                "proxies: []",
                "proxy-groups:",
                "  - name: PROXY",
                "    type: select",
                "    proxies:",
                "      - MISSING",
                "rules:",
                "  - MATCH,PROXY",
                "",
            ]
        ),
    )
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "clash.yaml proxy-groups[0] unknown reference: MISSING" in error
        for error in errors
    )


def test_validate_pages_artifact_reports_clash_unknown_rule_policy(
    tmp_path: Path,
) -> None:
    _write_valid_artifact(tmp_path)
    _write_text(
        tmp_path / "clash.yaml",
        "\n".join(
            [
                "port: 7890",
                "proxies: []",
                "proxy-groups:",
                "  - name: PROXY",
                "    type: select",
                "    proxies:",
                "      - DIRECT",
                "rules:",
                "  - MATCH,MISSING",
                "",
            ]
        ),
    )
    _write_manifest(tmp_path)

    errors = validate_pages_artifact(tmp_path)

    assert any(
        "clash.yaml rules[0] unknown policy: MISSING" in error for error in errors
    )


def test_validate_pages_artifact_native_check_skips_when_binaries_missing(
    tmp_path: Path, monkeypatch
) -> None:
    _write_valid_artifact(tmp_path)
    monkeypatch.setattr("scripts.validate_pages_artifact.shutil.which", lambda _: None)

    errors = validate_pages_artifact(tmp_path, native_client_check=True)

    assert errors == []


def test_validate_pages_artifact_native_check_reports_singbox_failure(
    tmp_path: Path, monkeypatch
) -> None:
    _write_valid_artifact(tmp_path)

    def fake_which(name: str) -> str | None:
        return "sing-box" if name == "sing-box" else None

    def fake_run(command, **kwargs):
        assert command[:3] == ["sing-box", "check", "-c"]

        class Result:
            returncode = 1
            stderr = "bad sing-box config"
            stdout = ""

        return Result()

    monkeypatch.setattr("scripts.validate_pages_artifact.shutil.which", fake_which)
    monkeypatch.setattr("scripts.validate_pages_artifact.subprocess.run", fake_run)

    errors = validate_pages_artifact(tmp_path, native_client_check=True)

    assert any(
        "singbox.json native client check failed: bad sing-box config" in error
        for error in errors
    )


def test_validate_pages_artifact_native_check_reports_mihomo_failure(
    tmp_path: Path, monkeypatch
) -> None:
    _write_valid_artifact(tmp_path)

    def fake_which(name: str) -> str | None:
        return "mihomo" if name == "mihomo" else None

    def fake_run(command, **kwargs):
        assert command[:3] == ["mihomo", "-t", "-f"]

        class Result:
            returncode = 1
            stderr = "bad clash config"
            stdout = ""

        return Result()

    monkeypatch.setattr("scripts.validate_pages_artifact.shutil.which", fake_which)
    monkeypatch.setattr("scripts.validate_pages_artifact.subprocess.run", fake_run)

    errors = validate_pages_artifact(tmp_path, native_client_check=True)

    assert any(
        "clash.yaml native client check failed: bad clash config" in error
        for error in errors
    )


def test_write_pages_contract_refreshes_mutated_artifact(tmp_path: Path) -> None:
    _write_valid_artifact(tmp_path)
    _write_text(tmp_path / "base64.txt", "changed after initial manifest")

    assert any(
        "artifact_manifest.json sha256 mismatch: base64.txt" in error
        for error in validate_pages_artifact(tmp_path)
    )

    write_pages_contract(tmp_path)

    errors = validate_pages_artifact(tmp_path)
    manifest = json.loads(
        (tmp_path / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    paths = {item["path"] for item in manifest["files"]}

    assert errors == []
    assert "base64.txt" in paths
