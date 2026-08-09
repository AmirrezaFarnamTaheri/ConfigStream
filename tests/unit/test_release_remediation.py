# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.finalize_release_outputs import finalize, modernize_singbox
from scripts.release_gate import validate
from scripts.shard_sources import partition


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_partition_is_deterministic_and_complete() -> None:
    lines = ["https://c.example/sub", "https://a.example/sub", "https://b.example/sub"]
    first = partition(lines, 4)
    second = partition(list(reversed(lines)), 4)
    assert first == second
    assert sorted(item for bucket in first for item in bucket) == sorted(lines)


def test_modernize_singbox_migrates_wireguard_and_route_contract() -> None:
    payload = {
        "inbounds": [{"type": "tun", "inet4_address": "172.19.0.1/30"}],
        "outbounds": [
            {
                "type": "http",
                "tag": "relay",
                "server": "127.0.0.1",
                "server_port": 8080,
            },
            {
                "type": "wireguard",
                "tag": "🛡️\u008f SECURE",
                "server": "162.159.192.1",
                "server_port": 2408,
                "local_address": "10.0.0.2/32",
                "private_key": "private",
                "peer_public_key": "public",
                "detour": "relay",
            },
            {
                "type": "selector",
                "tag": "🌍 Proxy Select",
                "outbounds": ["🛡️\u008f SECURE"],
            },
            {"type": "block", "tag": "block"},
            {"type": "dns", "tag": "dns-out"},
        ],
        "route": {"rules": [{"protocol": "dns", "outbound": "dns-out"}]},
    }
    result = modernize_singbox(payload)
    assert not any(item.get("type") == "wireguard" for item in result["outbounds"])
    assert not any(item.get("type") in {"block", "dns"} for item in result["outbounds"])
    assert result["endpoints"][0]["address"] == ["10.0.0.2/32"]
    assert result["route"]["final"] == "🌍 Proxy Select"
    assert any(item.get("action") == "hijack-dns" for item in result["route"]["rules"])
    assert result["inbounds"][0]["address"] == ["172.19.0.1/30"]
    assert "\u008f" not in json.dumps(result, ensure_ascii=False)


def test_finalize_sanitizes_counts_sources_and_transients(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    records = [
        {
            "id": "native",
            "protocol": "http",
            "address": "127.0.0.1",
            "port": 8080,
            "is_working": True,
            "source": "https://user:secret@example.com/sub?token=secret",
            "details": {"_source": "https://example.com/private"},
            "remarks": "native",
        },
        {
            "id": "chain",
            "protocol": "chain",
            "address": "162.159.192.1",
            "port": 2408,
            "is_working": True,
            "config": json.dumps(
                {
                    "outbounds": [
                        {
                            "type": "wireguard",
                            "tag": "wg",
                            "server": "162.159.192.1",
                            "server_port": 2408,
                            "local_address": ["10.0.0.2/32"],
                            "private_key": "private",
                            "peer_public_key": "public",
                        }
                    ]
                }
            ),
        },
    ]
    leaked_derivative = {
        "id": "revived",
        "protocol": "vless",
        "address": "203.0.113.8",
        "port": 443,
        "is_working": False,
        "details": {
            "tester_error_category": "IPC_ERROR",
            "failure_category": "TIMEOUT",
            "safe_public_field": "kept",
        },
    }
    write_json(output / "proxies.json", records)
    write_json(output / "countries" / "XX.list.json", [leaked_derivative])
    write_json(
        output / "protocols" / "revived.list-dns-safe.json", [leaked_derivative]
    )
    write_json(
        output / "metadata.json",
        {
            "total_tested": 2,
            "fetched_sources": 8,
            "total_configured_sources": 10,
            "time_limited": False,
            "shielded_count": 739,
            "shielded_candidate_count": 0,
            "shielded_verified_count": 0,
        },
    )
    write_json(
        output / "singbox.json",
        {
            "outbounds": [
                {
                    "type": "http",
                    "tag": "🌍 Proxy Select",
                    "server": "127.0.0.1",
                    "server_port": 8080,
                }
            ]
        },
    )
    (output / "clash.yaml").write_text(
        "proxies: []\nproxy-groups: []\n", encoding="utf-8"
    )
    (output / ".metadata.json.lock").write_text("", encoding="utf-8")
    finalize(output, tmp_path, 0.80)

    public = json.loads((output / "proxies.json").read_text(encoding="utf-8"))
    assert public[0]["source"] == "example.com"
    assert "_source" not in public[0]["details"]
    for derivative in (
        output / "countries" / "XX.list.json",
        output / "protocols" / "revived.list-dns-safe.json",
    ):
        payload = json.loads(derivative.read_text(encoding="utf-8"))
        assert payload[0]["details"] == {"safe_public_field": "kept"}
    metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["total_proxies"] == 1
    assert metadata["exported_record_count"] == 2
    assert metadata["total_working"] == 1
    assert metadata["exported_working_record_count"] == 2
    assert metadata["source_coverage"] == 0.8
    assert metadata["shard_shielded_candidate_count"] == 739
    assert metadata["shielded_count"] == 0
    assert metadata["shielded_candidate_count"] == 0
    assert metadata["shielded_verified_count"] == 0
    assert not list(output.rglob("*.lock"))
    assert (output / "xray.json").is_file()
    health = json.loads((output / "health.json").read_text(encoding="utf-8"))
    assert health["release_blockers"] == []


def test_release_gate_rejects_skipped_or_missing_native_validation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "output"
    root.mkdir()
    write_json(root / "proxies.json", [{"id": "p"}])
    write_json(
        root / "metadata.json",
        {
            "source_coverage": 1.0,
            "logical_total_working": 1,
            "time_limited": False,
            "shielded_candidate_count": 0,
            "shielded_verified_count": 0,
        },
    )
    write_json(root / "health.json", {"release_blockers": []})
    write_json(
        root / "format_compatibility.json",
        {
            "targets": {
                name: {"status": "generated"}
                for name in (
                    "sing-box",
                    "xray",
                    "mihomo",
                    "surge",
                    "loon",
                    "quantumult-x",
                )
            }
        },
    )
    for name in ("singbox.json", "xray.json"):
        write_json(root / name, {})
    (root / "clash.yaml").write_text("proxies: []\n", encoding="utf-8")
    files = []
    for path in root.iterdir():
        if path.name == "artifact_manifest.json":
            continue
        files.append(
            {
                "path": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    write_json(root / "artifact_manifest.json", {"files": files})
    report = tmp_path / "native.json"
    write_json(
        report,
        {
            "checks": [
                {"core": "sing-box", "path": "singbox.json", "status": "skipped"},
                {"core": "mihomo", "path": "clash.yaml", "status": "passed"},
            ]
        },
    )
    errors = validate(root, report, 0.8)
    assert any("did not pass" in error for error in errors)
    assert any("xray" in error for error in errors)
