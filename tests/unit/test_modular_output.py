# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path
from typing import List
import pytest

from configstream.models import Proxy
from configstream.output.metadata import generate_metadata_json


@pytest.fixture
def temp_output_dir(tmp_path):
    return tmp_path


def test_generate_metadata_json_basic(temp_output_dir):
    proxies = [
        Proxy(
            config="vless://1.1.1.1:443",
            protocol="vless",
            address="1.1.1.1",
            port=443,
            is_working=True,
            latency=100,
        ),
        Proxy(
            config="vmess://2.2.2.2:443",
            protocol="vmess",
            address="2.2.2.2",
            port=443,
            is_working=False,
        ),
    ]
    stats = {"fetched_lines": 10, "parsed": 5, "tested": 5}

    generate_metadata_json(stats, proxies, temp_output_dir)

    meta_path = temp_output_dir / "metadata.json"
    assert meta_path.exists()

    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema_version"] == "3.0.2"
    assert data["total_proxies"] == 2
    assert data["total_working"] == 1
    assert data["protocols"]["vless"] == 1
    assert "vmess" not in data["protocols"]  # because it's not working
    assert data["fetched_lines"] == 10


def test_generate_metadata_json_empty(temp_output_dir):
    generate_metadata_json({}, [], temp_output_dir)
    meta_path = temp_output_dir / "metadata.json"
    assert meta_path.exists()

    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_proxies"] == 0
    assert data["total_working"] == 0
