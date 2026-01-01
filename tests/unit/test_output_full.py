# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import patch
from configstream.output import (
    save_json,
    save_metadata,
    generate_split_outputs,
    generate_categorized_outputs,
)
from configstream.models import Proxy


@pytest.fixture
def proxies():
    p1 = Proxy(
        config="vless://1",
        protocol="vless",
        address="1.1.1.1",
        port=443,
        uuid="u1",
        is_working=True,
        latency=100,
        country_code="US",
        details={"security": "tls"},
        id="p1",
    )
    p2 = Proxy(
        config="vmess://2",
        protocol="vmess",
        address="2.2.2.2",
        port=80,
        uuid="u2",
        is_working=False,
        latency=None,
        country_code="DE",
        details={},
        id="p2",
    )
    return [p1, p2]


@pytest.fixture
def output_dir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    return d


def test_save_json(proxies, output_dir):
    path = output_dir / "proxies.json"
    with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:
        MockHistory.return_value.get_history.return_value = []
        save_json(proxies, path)

    assert path.exists()
    import json

    data = json.loads(path.read_text())
    assert len(data) == 2
    assert data[0]["protocol"] == "vless"


def test_save_json_compress(proxies, output_dir):
    path = output_dir / "proxies.json"
    with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:
        MockHistory.return_value.get_history.return_value = []
        save_json(proxies, path, compress=True)

    assert path.exists()
    gz_path = output_dir / "proxies.json.gz"
    assert gz_path.exists()

    import gzip
    import json

    with gzip.open(gz_path, "rt") as f:
        data = json.load(f)
        assert len(data) == 2


def test_save_metadata(proxies, output_dir):
    stats = {"working": 1, "fetched_lines": 10, "duration": 5.0}

    with patch("configstream.output_logic.version", return_value="1.0.0"):
        save_metadata(stats, proxies, output_dir)

    path = output_dir / "metadata.json"
    assert path.exists()
    import json

    data = json.loads(path.read_text())

    assert data["total_proxies"] == 2
    assert data["total_working"] == 1
    assert data["version"] == "1.0.0"
    # 100ms is < 200ms, so it falls into "fast" bin in current implementation
    assert data["latency_distribution"]["fast"] == 1
    assert data["latency_distribution"]["medium"] == 0
    assert "isp_stats" in data


def test_generate_split_outputs(proxies, output_dir):
    washed = [{"tag": "🛡️ Secure Washed", "type": "urltest"}]
    washed_ids = {"u2"}
    smart_chains = {"intranet": [], "ipv6": [], "streamer": []}

    with (
        patch("configstream.generators.singbox.to_singbox_outbound") as mock_conv,
        patch(
            "configstream.output_generators.generate_clash_config", return_value="clash"
        ),
    ):

        mock_conv.return_value = {"type": "vless", "tag": "vless-out"}

        files = generate_split_outputs(
            proxies, output_dir, washed, washed_ids, smart_chains
        )

        assert "singbox" in files
        assert "singbox_vpn" in files
        assert "clash" in files

        import json

        vpn_config = json.loads(files["singbox_vpn"].read_text())
        outbounds = vpn_config["outbounds"]
        auto_selector = next(o for o in outbounds if o["tag"] == "🚀 Auto")
        assert len(auto_selector["outbounds"]) == 1


@pytest.mark.asyncio
async def test_generate_categorized_outputs(proxies, output_dir):
    with (
        patch("configstream.output_logic.ProxyWasher") as MockWasher,
        patch(
            "configstream.output_logic.generate_smart_chains",
            return_value={"chains": []},
        ),
        patch(
            "configstream.output_logic.generate_split_outputs",
            return_value={"singbox": output_dir / "singbox.json"},
        ),
        patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory,
    ):  # Mock history to return serializable data

        # Configure mock history to return empty list (serializable)
        history_instance = MockHistory.return_value
        history_instance.get_history.return_value = []

        MockWasher.return_value.wash_batch.return_value = ([], set())

        files = generate_categorized_outputs(proxies, output_dir)

        assert "master" in files
        assert "proto_vless" in files
        assert "country_US" in files

        assert (output_dir / "by_protocol" / "vless.json").exists()
        assert (output_dir / "by_country" / "US.json").exists()
