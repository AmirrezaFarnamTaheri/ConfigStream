# SPDX-License-Identifier: AGPL-3.0-or-later
"""Xray chain references must be unambiguous and acyclic."""

from __future__ import annotations

import json

import pytest

from configstream.output.client_formats import (
    generate_xray_config,
    validate_xray_config,
)


def _hop(tag: str, *, detour: str = "", host: str = "relay.example") -> dict:
    hop = {"tag": tag, "type": "socks", "server": host, "server_port": 1080}
    if detour:
        hop["detour"] = detour
    return hop


def _render(outbounds: list[dict]):
    return generate_xray_config(
        [
            {
                "protocol": "chain",
                "is_working": True,
                "config": json.dumps({"outbounds": outbounds}),
            }
        ]
    )


@pytest.mark.parametrize(
    "hops",
    [
        [_hop("self", detour="self")],
        [_hop("a", detour="b"), _hop("b", detour="a")],
        [_hop("a", detour="b"), _hop("b", detour="c"), _hop("c", detour="a")],
    ],
)
def test_cyclic_xray_chain_is_not_exported(hops: list[dict]) -> None:
    config, report = _render(hops)
    assert report["emitted_records"] == 0
    assert report["unsupported"] == {"chain": 1}
    assert [item["tag"] for item in config["outbounds"]] == ["direct", "block"]


def test_ambiguous_duplicate_chain_tags_are_not_exported() -> None:
    config, report = _render(
        [
            _hop("relay", host="a.example"),
            _hop("relay", host="b.example"),
            _hop("exit", detour="relay"),
        ]
    )
    assert report["unsupported"] == {"chain": 1}
    assert [item["tag"] for item in config["outbounds"]] == ["direct", "block"]


def test_valid_two_hop_chain_is_preserved() -> None:
    config, report = _render([_hop("relay"), _hop("exit", detour="relay")])
    assert report["emitted_records"] == 1
    assert validate_xray_config(config) == []


def test_xray_validator_rejects_cycle_in_existing_json() -> None:
    config, _ = _render([_hop("relay"), _hop("exit", detour="relay")])
    config["outbounds"][0]["streamSettings"]["sockopt"] = {"dialerProxy": "exit"}
    errors = validate_xray_config(config)
    assert any("cycle" in error.lower() and "relay" in error for error in errors)
