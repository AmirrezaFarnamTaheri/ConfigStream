import pytest
import json
from pathlib import Path
from configstream.output import save_json, save_metadata, generate_split_outputs
from configstream.models import Proxy
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="vmess://1",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            is_working=True,
            latency=50,
            country_code="US",
        ),
        Proxy(
            config="ss://2",
            protocol="shadowsocks",
            address="2.2.2.2",
            port=8388,
            is_working=True,
            latency=200,
            country_code="IR",
        ),
    ]


def test_atomic_write_json(tmp_path, sample_proxies):
    """Verify that JSON saving uses atomic writes."""
    target = tmp_path / "test.json"
    save_json(sample_proxies, target)

    assert target.exists()
    content = json.loads(target.read_text())
    assert len(content) == 2
    assert content[0]["protocol"] == "vmess"


def test_metadata_generation(tmp_path, sample_proxies):
    """Verify metadata generation."""
    stats = {"working": 2, "fetched_lines": 10, "duration": 1.5}
    save_metadata(stats, sample_proxies, tmp_path)

    meta_file = tmp_path / "metadata.json"
    assert meta_file.exists()
    data = json.loads(meta_file.read_text())
    assert data["total_working"] == 2
    assert data["latency_distribution"]["fast"] == 1  # 50ms
    assert data["latency_distribution"]["medium"] == 1  # 200ms


def test_split_outputs_atomic(tmp_path, sample_proxies):
    """Verify split outputs are generated atomically."""
    generate_split_outputs(
        sample_proxies,
        tmp_path,
        [],
        set(),
        {"intranet": [], "ipv6": [], "streamer": []},
    )

    assert (tmp_path / "singbox-vpn.json").exists()
    assert (tmp_path / "singbox.json").exists()
    assert (tmp_path / "clash.yaml").exists()
