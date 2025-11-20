import pytest
from pathlib import Path
import json
from configstream.models import Proxy
from configstream.output import (
    to_clash_proxy,
    to_singbox_outbound,
    generate_clash_config,
    generate_singbox_config,
    save_metadata,
)


@pytest.fixture
def sample_proxies():
    p1 = Proxy(
        config="vmess://...",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        uuid="uuid-1",
        latency=50.0,  # 50ms
        is_working=True,
        country_code="US",
        details={"aid": 0, "net": "ws", "tls": "tls", "path": "/ws"},
    )
    p2 = Proxy(
        config="ss://...",
        protocol="shadowsocks",
        address="2.2.2.2",
        port=8388,
        latency=200.0,  # 200ms
        is_working=True,
        country_code="JP",
        details={"method": "aes-256-gcm", "password": "pass"},
    )
    p3 = Proxy(
        config="http://...",
        protocol="http",
        address="3.3.3.3",
        port=8080,
        latency=1500.0,  # 1.5s
        is_working=True,
        country_code="DE",
        details={},
    )
    return [p1, p2, p3]


def test_to_clash_proxy(sample_proxies):
    p1 = sample_proxies[0]
    clash = to_clash_proxy(p1)
    assert clash is not None
    assert clash["type"] == "vmess"
    assert clash["server"] == "1.1.1.1"
    assert clash["network"] == "ws"  # mapped from 'net'
    assert clash["tls"] is True

    p2 = sample_proxies[1]
    clash_ss = to_clash_proxy(p2)
    assert clash_ss["type"] == "ss"
    assert clash_ss["cipher"] == "aes-256-gcm"


def test_to_singbox_outbound(sample_proxies):
    p1 = sample_proxies[0]
    sing = to_singbox_outbound(p1)
    assert sing is not None
    assert sing["type"] == "vmess"
    assert sing["server"] == "1.1.1.1"
    # singbox format check


def test_generate_clash_config(sample_proxies):
    yaml_out = generate_clash_config(sample_proxies)
    assert "proxies:" in yaml_out
    assert "proxy-groups:" in yaml_out
    assert "US 01 | VMESS" in yaml_out


def test_generate_singbox_config(sample_proxies):
    json_out = generate_singbox_config(sample_proxies)
    data = json.loads(json_out)
    assert "outbounds" in data
    # Index 0 and 1 are Selector and URLTest
    assert data["outbounds"][2]["tag"] == "US 01 | VMESS"


def test_save_metadata(tmp_path, sample_proxies):
    stats = {"working": 3, "fetched_lines": 10, "duration": 5.5}
    save_metadata(stats, sample_proxies, tmp_path)

    meta_file = tmp_path / "metadata.json"
    assert meta_file.exists()

    data = json.loads(meta_file.read_text())
    assert data["total_working"] == 3
    assert data["total_fetched"] == 10
    assert data["countries"]["US"] == 1
    assert data["protocols"]["vmess"] == 1

    # Latency buckets check
    # p1 (0.05s = 50ms) -> fast (<100)
    # p2 (0.2s = 200ms) -> medium (100-500)
    # p3 (1.5s = 1500ms) -> very_slow (>1000)
    dist = data["latency_distribution"]
    assert dist["fast"] == 1
    assert dist["medium"] == 1
    assert dist["slow"] == 0
    assert dist["very_slow"] == 1
