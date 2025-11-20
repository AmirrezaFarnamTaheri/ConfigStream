
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from configstream.models import Proxy
from configstream.output import save_metadata

def test_save_metadata_analytics_structure(tmp_path: Path):
    """
    Verify that save_metadata generates the correct structure for analytics.js.
    """
    # Create mock proxies with various latencies
    proxies = []

    # Fast proxy (<100ms)
    p1 = Proxy(config="vmess://mock1", protocol="vmess", address="1.1.1.1", port=80)
    p1.latency_ms = 50
    p1.country_code = "US"
    proxies.append(p1)

    # Medium proxy (100-500ms)
    p2 = Proxy(config="ss://mock2", protocol="ss", address="2.2.2.2", port=443)
    p2.latency_ms = 250
    p2.country_code = "DE"
    proxies.append(p2)

    # Slow proxy (500-1000ms)
    p3 = Proxy(config="trojan://mock3", protocol="trojan", address="3.3.3.3", port=443)
    p3.latency_ms = 750
    p3.country_code = "US"
    proxies.append(p3)

    # Very slow proxy (>1000ms)
    p4 = Proxy(config="vless://mock4", protocol="vless", address="4.4.4.4", port=443)
    p4.latency_ms = 1500
    p4.country_code = "JP"
    proxies.append(p4)

    # No latency proxy (should be counted as very slow/unknown)
    p5 = Proxy(config="vmess://mock5", protocol="vmess", address="5.5.5.5", port=80)
    p5.latency_ms = None
    p5.country_code = "CN"
    proxies.append(p5)

    stats = {
        "working": 5,
        "fetched_lines": 100,
        "duration": 10.5
    }

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    save_metadata(stats, proxies, output_dir)

    metadata_file = output_dir / "metadata.json"
    assert metadata_file.exists()

    data = json.loads(metadata_file.read_text())

    # Check basic stats
    assert data["total_proxies"] == 5
    assert data["total_working"] == 5
    assert data["total_fetched"] == 100
    assert data["duration_seconds"] == 10.5
    assert "last_updated_utc" in data

    # Check latency distribution
    dist = data["latency_distribution"]
    assert dist["fast"] == 1
    assert dist["medium"] == 1
    assert dist["slow"] == 1
    assert dist["very_slow"] == 2  # 1500ms + None

    # Check protocol breakdown
    assert data["protocols"]["vmess"] == 2
    assert data["protocols"]["ss"] == 1
    assert data["protocols"]["trojan"] == 1
    assert data["protocols"]["vless"] == 1

    # Check country breakdown
    assert data["countries"]["US"] == 2
    assert data["countries"]["DE"] == 1
    assert data["countries"]["JP"] == 1
    assert data["countries"]["CN"] == 1

    # Check protocol colors existence
    assert "protocol_colors" in data
    assert "vmess" in data["protocol_colors"]
