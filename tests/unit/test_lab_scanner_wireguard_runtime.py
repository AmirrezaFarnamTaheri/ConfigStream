# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCANNER_PATH = ROOT / "tools" / "lab-scanner.py"
VALID_PRIVATE_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


def _load_scanner():
    spec = importlib.util.spec_from_file_location("configstream_lab_scanner", SCANNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lab_scanner_does_not_embed_shared_wireguard_private_key() -> None:
    text = SCANNER_PATH.read_text(encoding="utf-8")
    assert "YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=" not in text


def test_lab_scanner_emits_singbox_113_wireguard_endpoint(monkeypatch) -> None:
    scanner = _load_scanner()
    monkeypatch.delenv("WARP_KEY_POOL", raising=False)
    config = scanner.generate_chain_config(
        [
            {
                "type": "warp",
                "ip": "1.1.1.1",
                "port": 2408,
                "private_key": VALID_PRIVATE_KEY,
            }
        ]
    )

    assert [item["type"] for item in config["outbounds"]] == ["direct"]
    assert config["route"]["final"] == "layer-1"
    assert len(config["endpoints"]) == 1
    endpoint = config["endpoints"][0]
    assert endpoint["type"] == "wireguard"
    assert endpoint["tag"] == "layer-1"
    assert endpoint["address"] == ["172.16.0.2/32"]
    assert endpoint["private_key"] == VALID_PRIVATE_KEY
    assert "server" not in endpoint
    assert endpoint["peers"][0]["address"] == "1.1.1.1"
    assert endpoint["peers"][0]["port"] == 2408
    assert endpoint["peers"][0]["allowed_ips"] == ["0.0.0.0/0"]


def test_lab_scanner_uses_existing_warp_key_pool(monkeypatch) -> None:
    scanner = _load_scanner()
    monkeypatch.setenv(
        "WARP_KEY_POOL",
        json.dumps(
            [
                {
                    "private_key": VALID_PRIVATE_KEY,
                    "reserved": [1, 2, 3],
                }
            ]
        ),
    )
    config = scanner.generate_chain_config(
        [{"type": "warp", "ip": "8.8.8.8", "port": 2408}]
    )

    peer = config["endpoints"][0]["peers"][0]
    assert config["endpoints"][0]["private_key"] == VALID_PRIVATE_KEY
    assert peer["reserved"] == [1, 2, 3]


def test_lab_scanner_requires_real_warp_credentials(monkeypatch) -> None:
    scanner = _load_scanner()
    monkeypatch.delenv("WARP_KEY_POOL", raising=False)

    with pytest.raises(ValueError, match="WARP private key is required"):
        scanner.generate_chain_config(
            [{"type": "warp", "ip": "1.1.1.1", "port": 2408}]
        )
