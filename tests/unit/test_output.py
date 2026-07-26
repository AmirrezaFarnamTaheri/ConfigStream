# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import json
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from unittest.mock import MagicMock
from configstream.output_transport import save_json
from configstream.output_logic import (
    save_metadata,
    generate_categorized_outputs,
    write_public_artifact_contract,
)
from configstream.models import Proxy
from configstream.pipeline_stats import PipelineStats
from configstream.quality.storage import QualityStorage
from scripts.finalize_release_outputs import finalize
from scripts.validate_pages_artifact import validate_pages_artifact


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="vmess://1",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            uuid="dummy",
            is_working=True,
            latency=50,
            country_code="US",
        ),
        Proxy(
            config="ss://2",
            protocol="shadowsocks",
            address="2.2.2.2",
            port=8388,
            password="dummy",
            is_working=True,
            latency=200,
            country_code="IR",
        ),
    ]


@pytest.fixture
def mock_storage():
    return MagicMock(spec=QualityStorage)


def test_atomic_write_json(tmp_path, sample_proxies):
    """Verify that JSON saving uses atomic writes."""
    target = tmp_path / "test.json"
    save_json(sample_proxies, target)

    assert target.exists()
    content = json.loads(target.read_text())
    assert len(content) == 2
    assert content[0]["protocol"] == "vmess"


def test_metadata_generation(tmp_path, sample_proxies, mock_storage):
    """Verify metadata generation."""
    stats = PipelineStats(fetched_lines=10, scanner_ips_found=5)
    stats.working = 2

    save_metadata(stats, sample_proxies, tmp_path)

    meta_file = tmp_path / "metadata.json"
    assert meta_file.exists()
    data = json.loads(meta_file.read_text())
    assert data["total_working"] == 2
    assert data["latency_distribution"]["fast"] == 1
    assert data["latency_distribution"]["medium"] == 1
    assert len(data["proxies_snapshot_hash"]) == 64
    assert data["previous_proxies_snapshot_hash"] is None


def test_metadata_includes_previous_proxy_snapshot_hash(tmp_path, sample_proxies):
    """Metadata records old proxy snapshot identity for diff clients."""
    old_payload = [{"id": "old", "protocol": "vless"}]
    (tmp_path / "proxies.old.json").write_text(
        json.dumps(old_payload), encoding="utf-8"
    )

    save_metadata(PipelineStats(fetched_lines=10), sample_proxies, tmp_path)

    data = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert len(data["proxies_snapshot_hash"]) == 64
    assert len(data["previous_proxies_snapshot_hash"]) == 64
    assert data["previous_proxies_snapshot_hash"] != data["proxies_snapshot_hash"]


def test_metadata_does_not_count_shielded_candidates_as_working(
    tmp_path, sample_proxies
):
    """Shielded candidates are not working until explicitly retested."""
    stats = {
        "working": 2,
        "tested": 4,
        "fetched_lines": 10,
        "shielded_count": 3,
        "shielded_verified_count": 1,
    }

    save_metadata(stats, sample_proxies, tmp_path)

    data = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert data["total_working"] == 2
    assert data["total_valid_proxies"] == 2
    assert data["shielded_count"] == 3
    assert data["shielded_candidate_count"] == 3
    assert data["shielded_verified_count"] == 1
    assert data["success_rate"] == 0.5


def test_public_artifact_contract_generation(tmp_path, sample_proxies):
    """Verify health and artifact manifest are generated from output files."""
    stats = PipelineStats(fetched_lines=10)
    stats.working = 2
    save_metadata(stats, sample_proxies, tmp_path)
    (tmp_path / "base64.txt").write_text("dm1lc3M6Ly8x", encoding="utf-8")

    manifest = write_public_artifact_contract(tmp_path)

    health = json.loads((tmp_path / "health.json").read_text(encoding="utf-8"))
    saved_manifest = json.loads(
        (tmp_path / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    paths = {entry["path"] for entry in saved_manifest["files"]}

    assert health["status"] == "ok"
    assert health["total_working"] == 2
    assert manifest["file_count"] == saved_manifest["file_count"]
    assert "metadata.json" in paths
    assert "health.json" in paths
    assert "base64.txt" in paths
    assert all(entry["sha256"] for entry in saved_manifest["files"])


def test_public_artifact_contract_includes_signature_when_key_configured(
    tmp_path, sample_proxies, monkeypatch
):
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_hex = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()
    monkeypatch.setenv("CS_SIGNING_PRIVATE_KEY_HEX", private_hex)

    stats = PipelineStats(fetched_lines=10)
    save_metadata(stats, sample_proxies, tmp_path)
    write_public_artifact_contract(tmp_path)

    saved_manifest = json.loads(
        (tmp_path / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    signature = saved_manifest.get("manifest_signature")
    assert isinstance(signature, dict)
    assert signature.get("algorithm") == "ed25519"
    assert isinstance(signature.get("signature"), str)


def test_split_outputs_atomic(tmp_path, sample_proxies):
    """Verify split outputs are generated atomically."""
    generate_categorized_outputs(
        sample_proxies,
        tmp_path,
        [],
        set(),
        {"intranet": [], "ipv6": [], "streamer": []},
    )

    assert (tmp_path / "singbox.json").exists()
    assert (tmp_path / "clash.yaml").exists()
    assert (tmp_path / "chains.json").read_text(encoding="utf-8") == (
        tmp_path / "singbox-chains.json"
    ).read_text(encoding="utf-8")
    assert (tmp_path / "chains-dns-safe.json").read_text(encoding="utf-8") == (
        tmp_path / "singbox-chains-dns-safe.json"
    ).read_text(encoding="utf-8")
    assert (tmp_path / "chains-dns-hardened.json").read_text(encoding="utf-8") == (
        tmp_path / "singbox-chains-dns-hardened.json"
    ).read_text(encoding="utf-8")


def test_generated_public_artifact_fixture_matches_pages_contract(tmp_path):
    """Generate a deterministic public artifact and validate the full Pages contract."""
    proxies = [
        Proxy(
            config=(
                "vless://123e4567-e89b-12d3-a456-426614174000@1.1.1.1:443"
                "?security=tls&sni=example.com#fixture-vless"
            ),
            protocol="vless",
            address="1.1.1.1",
            port=443,
            uuid="123e4567-e89b-12d3-a456-426614174000",
            is_working=True,
            latency=42,
            country_code="US",
            resolved_ip="1.1.1.1",
            remarks="fixture-vless",
            details={"security": "tls", "sni": "example.com"},
        ),
        Proxy(
            config="http://8.8.8.8:8388#fixture-http",
            protocol="http",
            address="8.8.8.8",
            port=8388,
            is_working=True,
            latency=88,
            country_code="US",
            resolved_ip="8.8.8.8",
            remarks="fixture-http",
            details={},
        ),
        Proxy(
            config="socks5://162.159.192.1:2408#fixture-socks",
            protocol="socks5",
            address="162.159.192.1",
            port=2408,
            is_working=True,
            latency=120,
            country_code="US",
            resolved_ip="162.159.192.1",
            remarks="fixture-socks",
            details={},
        ),
        Proxy(
            config="client\nremote 9.9.9.9 1194 udp\n<ca>\nfixture\n</ca>\n",
            protocol="openvpn",
            address="9.9.9.9",
            port=1194,
            is_working=True,
            latency=140,
            country_code="US",
            resolved_ip="9.9.9.9",
            remarks="fixture-ovpn",
        ),
    ]

    generate_categorized_outputs(proxies, tmp_path, smart_chains={})
    save_json(proxies, tmp_path / "proxies.json")

    stats = PipelineStats(fetched_lines=len(proxies))
    stats.tested = len(proxies)
    stats.working = len(proxies)
    save_metadata(stats, proxies, tmp_path)
    finalize(tmp_path, tmp_path, 0.0)

    api_dir = tmp_path / "api"
    api_dir.mkdir(exist_ok=True)
    (api_dir / "proxies").write_text(
        (tmp_path / "proxies.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (api_dir / "stats").write_text(
        (tmp_path / "metadata.json").read_text(encoding="utf-8"), encoding="utf-8"
    )

    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    for name in (
        "clean_ips.json",
        "proxy_history_viz.json",
        "active_proxy_trend.json",
        "evasion_trend.json",
    ):
        (data_dir / name).write_text("[]", encoding="utf-8")

    docs_dir = tmp_path / "docs" / "wiki"
    docs_dir.mkdir(parents=True)
    (docs_dir / "index.md").write_text("# Fixture docs\n", encoding="utf-8")
    (tmp_path / "index.html").write_text(
        "<!doctype html><title>Fixture</title>", encoding="utf-8"
    )
    runtime_config_dir = tmp_path / "assets" / "js"
    runtime_config_dir.mkdir(parents=True)
    (runtime_config_dir / "runtime-config.js").write_text(
        "window.CS_RUNTIME_CONFIG = { PUBLIC_KEY: 'x' };",
        encoding="utf-8",
    )
    (tmp_path / "pipeline_events.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-06-13T00:00:00+00:00",
                "event_type": "pipeline_complete",
                "message": "Generated public artifact fixture.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    write_public_artifact_contract(tmp_path)

    assert validate_pages_artifact(tmp_path) == []
