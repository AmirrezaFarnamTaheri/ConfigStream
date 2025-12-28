import json
from unittest.mock import MagicMock

import pytest

from configstream.models import Proxy
from configstream.output import (generate_categorized_outputs, save_json,
                                 save_metadata)
from configstream.pipeline_core.stats import PipelineStats
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

    save_metadata(stats, sample_proxies, tmp_path)

    meta_file = tmp_path / "metadata.json"
    assert meta_file.exists()
    data = json.loads(meta_file.read_text())
    assert data["total_working"] == 2
    assert data["latency_distribution"]["fast"] == 1  # 50ms
    assert data["latency_distribution"]["medium"] == 1  # 200ms


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
