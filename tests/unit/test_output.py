# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import json
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


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="vmess://1",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            uuid="dummy",  # Add UUID for valid conversion
            is_working=True,
            latency=50,
            country_code="US",
        ),
        Proxy(
            config="ss://2",
            protocol="shadowsocks",
            address="2.2.2.2",
            port=8388,
            password="dummy",  # Add password
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
    stats.working = 2  # Set working count explicitly for test

    save_metadata(stats, sample_proxies, tmp_path)

    meta_file = tmp_path / "metadata.json"
    assert meta_file.exists()
    data = json.loads(meta_file.read_text())
    assert data["total_working"] == 2
    assert data["latency_distribution"]["fast"] == 1  # 50ms
    assert data["latency_distribution"]["medium"] == 1  # 200ms


def test_metadata_does_not_count_shielded_candidates_as_working(
    tmp_path, sample_proxies
):
    """Shielded candidates are not working until explicitly retested."""
    stats = {
        "working": 2,
        "tested": 4,
        "fetched_lines": 10,
        "shielded_count": 3,
    }

    save_metadata(stats, sample_proxies, tmp_path)

    data = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert data["total_working"] == 2
    assert data["total_valid_proxies"] == 2
    assert data["shielded_count"] == 3
    assert data["shielded_candidate_count"] == 3
    assert data["shielded_verified_count"] == 0
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


def test_split_outputs_atomic(tmp_path, sample_proxies):
    """Verify split outputs are generated atomically."""
    generate_categorized_outputs(
        sample_proxies,
        tmp_path,
        [],
        set(),
        {"intranet": [], "ipv6": [], "streamer": []},
    )

    # v2.0 file names
    assert (tmp_path / "singbox.json").exists()
    assert (tmp_path / "clash.yaml").exists()
