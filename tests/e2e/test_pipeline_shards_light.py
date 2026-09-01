# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lightweight sharded pipeline integration test for CI/CD.

Exercises the full producer-consumer pipeline, shard partitioning, per-shard
execution, shard health and lineage aggregation, batch merging, and schema validation
over 1-2 small deterministic shards without external network dependencies.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

import jsonschema
import pytest
from click.testing import CliRunner

from configstream.cli import merge as cli_merge
from configstream.geoip import GeoData
from configstream.pipeline import run_full_pipeline
from scripts.merge_batches import merge_batches
from scripts.shard_sources import partition

REPO_ROOT = Path(__file__).resolve().parents[2]
PROXY_LIST_SCHEMA_PATH = REPO_ROOT / "schema" / "proxy-list.schema.json"
METADATA_SCHEMA_PATH = REPO_ROOT / "schema" / "metadata.schema.json"
PROXY_SCHEMA_PATH = REPO_ROOT / "schema" / "proxy.schema.json"


import base64


def _sample_configs() -> List[str]:
    """Return a curated set of valid multi-protocol proxy lines distributed across shards."""
    vmess_payload_1 = {
        "v": "2",
        "ps": "VMess-Node-1",
        "add": "2.2.2.2",
        "port": "443",
        "id": "223e4567-e89b-42d3-a456-426614174000",
        "aid": 0,
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "vmess.example.com",
        "path": "/ws",
        "tls": "tls",
        "sni": "vmess.example.com",
    }
    vmess_b64_1 = base64.b64encode(json.dumps(vmess_payload_1).encode("utf-8")).decode(
        "utf-8"
    )

    vmess_payload_2 = {
        "v": "2",
        "ps": "VMess-Node-2",
        "add": "2.2.2.2",
        "port": "8443",
        "id": "223e4567-e89b-42d3-a456-426614174001",
        "aid": 0,
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "vmess2.example.com",
        "path": "/ws",
        "tls": "tls",
        "sni": "vmess2.example.com",
    }
    vmess_b64_2 = base64.b64encode(json.dumps(vmess_payload_2).encode("utf-8")).decode(
        "utf-8"
    )

    return [
        # VLESS Reality
        (
            "vless://123e4567-e89b-42d3-a456-426614174000@1.1.1.1:443"
            "?security=reality&encryption=none&pbk=pubkey123&sid=1234abcd"
            "&fp=chrome&type=tcp&sni=vless.example.com#VLESS-Node-1"
        ),
        (
            "vless://123e4567-e89b-42d3-a456-426614174003@1.1.1.1:443"
            "?security=reality&encryption=none&pbk=pubkey123&sid=1234abcd"
            "&fp=chrome&type=tcp&sni=vless.example.com#VLESS-Node-3"
        ),
        # VMess WS
        f"vmess://{vmess_b64_1}",
        f"vmess://{vmess_b64_2}",
        # Trojan TLS
        "trojan://trojanpassword@3.3.3.3:443?security=tls&type=tcp&sni=trojan.example.com#Trojan-Node",
        # Shadowsocks AEAD (Public IP)
        "ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMjIwLjE4MS4zOC4xNDg6ODM4OA#SS-Node",
        # Hysteria2
        "hysteria2://hyspassword@4.4.4.4:443?sni=hys.example.com&obfs=salamander&obfs-password=sec#Hys2-Node",
        # WireGuard
        (
            "wireguard://5.5.5.5:51820?peer_public_key=bmXOC%2BF1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="
            "&private_key=6M6tfYfQ6B0fLF8A3XJ2Z2z8jz4Yb9k%2Bf0z8xN2aM0E="
            "&reserved=[1,2,3]&local_address=10.0.0.2/24#WG-Node"
        ),
    ]


def _write_shard_lineage(
    output_dir: Path,
    *,
    batch: str,
    part: int,
    source_file: str,
    source_count: int,
    started_at: str,
    completed_at: str,
    exit_code: int = 0,
) -> None:
    """Record shard lineage artifact mimicking main CI pipeline execution."""
    payload = {
        "batch": batch,
        "part": part,
        "source_file": source_file,
        "source_count": source_count,
        "source_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "run_id": "test-run",
        "run_attempt": "1",
        "source_commit": "0000000000000000000000000000000000000000",
        "started_at": started_at,
        "completed_at": completed_at,
        "exit_code": exit_code,
        "status": "success" if exit_code == 0 else "failed",
    }
    lineage_path = output_dir / "shard_lineage.json"
    lineage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.fixture(autouse=True)
def _setup_hermetic_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock external network calls for reproducible, offline-safe pipeline tests."""
    monkeypatch.setenv("ENABLE_WASHER", "false")
    monkeypatch.setenv("ENABLE_WARP_REVIVAL", "false")
    monkeypatch.setenv("ENABLE_VWARP_REVIVAL", "false")
    monkeypatch.setenv("USE_VWARP_TUNNEL", "false")
    monkeypatch.setenv("ALLOW_ACTIVE_SCANNING", "false")

    async def fake_lookup(self: Any, ip: str) -> GeoData:
        ip_str = str(ip)
        if "1.1.1.1" in ip_str:
            return GeoData(
                country_code="US",
                country_name="United States",
                city="Los Angeles",
                asn="AS13335",
            )
        if "2.2.2.2" in ip_str:
            return GeoData(
                country_code="DE",
                country_name="Germany",
                city="Frankfurt",
                asn="AS24940",
            )
        if "3.3.3.3" in ip_str:
            return GeoData(
                country_code="SG",
                country_name="Singapore",
                city="Singapore",
                asn="AS45102",
            )
        return GeoData(
            country_code="NL",
            country_name="Netherlands",
            city="Amsterdam",
            asn="AS1103",
        )

    async def fake_update() -> None:
        return None

    async def fake_fetch_clean_ips(self: Any) -> None:
        return None

    monkeypatch.setattr("configstream.geoip.GeoIPResolver.lookup", fake_lookup)
    monkeypatch.setattr("configstream.pipeline.DEFAULT_BLOCKLIST.update", fake_update)
    monkeypatch.setattr(
        "configstream.intelligence.washer.core.ProxyWasher.fetch_clean_ips",
        fake_fetch_clean_ips,
    )


@pytest.mark.asyncio
async def test_light_sharded_pipeline_e2e(tmp_path: Path) -> None:
    """Run a light full pipeline partitioned across 2 shards and verify merge + schema."""
    configs = _sample_configs()
    shards = partition(configs, parts=2)
    assert len(shards) == 2
    assert all(len(bucket) > 0 for bucket in shards)

    shard_dirs: list[Path] = []

    # 1. Execute Pipeline for each Shard (Shard 1 and Shard 2)
    for index, bucket in enumerate(shards, start=1):
        shard_src = tmp_path / f"batch_light_part_{index}.txt"
        shard_src.write_text("\n".join(bucket) + "\n", encoding="utf-8")

        shard_out = tmp_path / f"output_batch_light_part_{index}"
        shard_out.mkdir(parents=True, exist_ok=True)
        shard_dirs.append(shard_out)

        started_at = datetime.now(timezone.utc).isoformat()

        # Run pipeline in dry-run mode (hermetic, parses, validates, dedupes, generates outputs)
        result = await run_full_pipeline(
            sources=[str(shard_src)],
            output_dir=str(shard_out),
            dry_run=True,
        )

        completed_at = datetime.now(timezone.utc).isoformat()

        assert result.success is True, f"Shard {index} failed: {result.error}"
        assert result.stats.final_count >= 1, f"Shard {index} produced 0 proxies"

        # Verify per-shard output artifacts
        assert (shard_out / "proxies.json").exists()
        assert (shard_out / "metadata.json").exists()
        assert (shard_out / "pipeline_events.jsonl").exists()

        # Write shard lineage and fake fetch summary log for reconciliation
        _write_shard_lineage(
            shard_out,
            batch="light",
            part=index,
            source_file=str(shard_src),
            source_count=len(bucket),
            started_at=started_at,
            completed_at=completed_at,
        )
        log_file = tmp_path / f"pipeline_batch_light_part_{index}.log"
        log_file.write_text(
            f"Fetch Summary: {len(bucket)}/{len(bucket)} sources successful\n",
            encoding="utf-8",
        )

    # 2. Merge Shards into Consolidated Output Directory
    merged_output = tmp_path / "merged_output"
    merged_output.mkdir(parents=True, exist_ok=True)

    batch_glob_pattern = str(tmp_path / "output_batch_light_part_*")
    await asyncio.to_thread(merge_batches, batch_glob_pattern, str(merged_output))

    # 3. Verify Merged Files
    merged_proxies_file = merged_output / "proxies.json"
    merged_metadata_file = merged_output / "metadata.json"
    assert merged_proxies_file.exists(), "Merged proxies.json missing"
    assert merged_metadata_file.exists(), "Merged metadata.json missing"

    merged_proxies = json.loads(merged_proxies_file.read_text(encoding="utf-8"))
    merged_metadata = json.loads(merged_metadata_file.read_text(encoding="utf-8"))

    assert isinstance(merged_proxies, list)
    assert len(merged_proxies) >= len(configs)

    # Verify multi-protocol diversity in merged output
    protocols_found = {p["protocol"] for p in merged_proxies}
    expected_protocols = {
        "vless",
        "vmess",
        "trojan",
        "shadowsocks",
        "hysteria2",
        "wireguard",
    }
    assert expected_protocols.issubset(
        protocols_found
    ), f"Missing expected protocols in merged output: {expected_protocols - protocols_found}"

    # Verify metadata aggregation
    assert merged_metadata.get("final_count") == len(configs)
    assert merged_metadata.get("total_proxies") == len(merged_proxies)
    assert merged_metadata.get("parsed", 0) >= len(configs)

    # 4. JSON Schema Validation on Merged Artifacts
    if PROXY_SCHEMA_PATH.is_file():
        proxy_schema = json.loads(PROXY_SCHEMA_PATH.read_text(encoding="utf-8"))
        proxy_validator = jsonschema.Draft202012Validator(proxy_schema)
        for proxy in merged_proxies:
            proxy_validator.validate(proxy)

        if PROXY_LIST_SCHEMA_PATH.is_file():
            proxy_list_schema = json.loads(
                PROXY_LIST_SCHEMA_PATH.read_text(encoding="utf-8")
            )
            from referencing import Registry, Resource

            resource = Resource.from_contents(proxy_schema)
            registry = Registry().with_resources(
                [
                    ("proxy.schema.json", resource),
                    ("https://configstream.dev/schema/proxy.schema.json", resource),
                ]
            )
            validator = jsonschema.Draft202012Validator(
                proxy_list_schema, registry=registry
            )
            validator.validate(merged_proxies)

    if METADATA_SCHEMA_PATH.is_file():
        metadata_schema = json.loads(METADATA_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(metadata_schema).validate(merged_metadata)

    # 5. Verify Generated Subscriptions and Output Formats
    sub_dir = merged_output / "sub"
    if sub_dir.exists():
        expected_subs = ["all.txt", "sing-box.json", "clash.yaml"]
        for sub_name in expected_subs:
            sub_path = sub_dir / sub_name
            if sub_path.exists():
                assert (
                    sub_path.stat().st_size > 0
                ), f"Empty subscription file: {sub_name}"


def test_cli_light_pipeline_shard(tmp_path: Path) -> None:
    """Verify that the CLI entrypoint can execute a light single-shard pipeline run."""
    source_file = tmp_path / "cli_sources.txt"
    source_file.write_text(
        "vless://11111111-1111-1111-1111-111111111111@1.1.1.1:443"
        "?security=reality&encryption=none&pbk=pubkey123&sid=1234abcd"
        "&fp=chrome&type=tcp&sni=vless.example.com#CLI-Node\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "cli_output"

    runner = CliRunner()
    result = runner.invoke(
        cli_merge,
        [
            "--sources",
            str(source_file),
            "--output",
            str(output_dir),
            "--dry-run",
            "--allow-unadmitted-sources",
        ],
    )
    assert result.exit_code == 0, f"CLI invocation failed:\n{result.output}"
    assert (output_dir / "proxies.json").exists()
    assert (output_dir / "metadata.json").exists()
