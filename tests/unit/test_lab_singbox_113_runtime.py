# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import socket

import pytest
from fastapi import HTTPException

from configstream.lab_validation import _validate_and_build_lab_config
from configstream.testers.lab_chain_tester import (
    _ensure_config_ready,
    _is_private_or_local,
)


@pytest.mark.asyncio
async def test_live_lab_migrates_wireguard_and_removes_legacy_block() -> None:
    clean = await _validate_and_build_lab_config(
        {
            "outbounds": [
                {
                    "type": "vless",
                    "tag": "proxy-chain",
                    "server": "1.1.1.1",
                    "server_port": 443,
                    "uuid": "123e4567-e89b-12d3-a456-426614174000",
                    "detour": "warp-out",
                },
                {
                    "type": "wireguard",
                    "tag": "warp-out",
                    "server": "8.8.8.8",
                    "server_port": 2408,
                    "local_address": [
                        "172.16.0.2/32",
                        "fd01:db8:85a3::2/128",
                    ],
                    "private_key": "private",
                    "peer_public_key": "public",
                    "reserved": [1, 2, 3],
                    "mtu": 1280,
                },
                {"type": "block", "tag": "block"},
            ]
        }
    )

    assert [item["type"] for item in clean["outbounds"]] == ["vless"]
    assert clean["outbounds"][0]["detour"] == "warp-out"
    assert clean["route"] == {"final": "proxy-chain"}

    assert len(clean["endpoints"]) == 1
    endpoint = clean["endpoints"][0]
    assert endpoint["type"] == "wireguard"
    assert endpoint["tag"] == "warp-out"
    assert endpoint["address"] == [
        "172.16.0.2/32",
        "fd01:db8:85a3::2/128",
    ]
    assert "server" not in endpoint
    assert endpoint["peers"][0]["address"] == "8.8.8.8"
    assert endpoint["peers"][0]["port"] == 2408
    assert endpoint["peers"][0]["public_key"] == "public"
    assert endpoint["peers"][0]["allowed_ips"] == ["0.0.0.0/0", "::/0"]


@pytest.mark.asyncio
async def test_live_lab_preserves_wireguard_first_route_target() -> None:
    clean = await _validate_and_build_lab_config(
        {
            "outbounds": [
                {
                    "type": "wireguard",
                    "tag": "warp-primary",
                    "server": "8.8.8.8",
                    "server_port": 2408,
                    "local_address": ["172.16.0.2/32"],
                    "private_key": "private",
                    "peer_public_key": "public",
                },
                {
                    "type": "vless",
                    "tag": "fallback",
                    "server": "1.1.1.1",
                    "server_port": 443,
                    "uuid": "123e4567-e89b-12d3-a456-426614174000",
                },
            ]
        }
    )

    assert clean["route"] == {"final": "warp-primary"}
    assert [endpoint["tag"] for endpoint in clean["endpoints"]] == ["warp-primary"]
    assert [outbound["tag"] for outbound in clean["outbounds"]] == ["fallback"]


@pytest.mark.asyncio
async def test_live_lab_rejects_private_wireguard_peer_destination() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await _validate_and_build_lab_config(
            {
                "outbounds": [
                    {
                        "type": "wireguard",
                        "tag": "warp-out",
                        "server": "8.8.8.8",
                        "server_port": 2408,
                        "local_address": ["172.16.0.2/32"],
                        "private_key": "private",
                        "peer_public_key": "public",
                        "peers": [
                            {
                                "address": "127.0.0.1",
                                "port": 2408,
                                "public_key": "public",
                            }
                        ],
                    }
                ]
            }
        )

    assert exc_info.value.status_code == 400
    assert "peers[0].address" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_live_lab_wireguard_peers_share_resolution_budget() -> None:
    peers = [
        {
            "address": "8.8.8.8",
            "port": 2408,
            "public_key": f"peer-{index}",
        }
        for index in range(64)
    ]
    with pytest.raises(HTTPException) as exc_info:
        await _validate_and_build_lab_config(
            {
                "outbounds": [
                    {
                        "type": "wireguard",
                        "tag": "warp-out",
                        "server": "8.8.8.8",
                        "server_port": 2408,
                        "local_address": ["172.16.0.2/32"],
                        "private_key": "private",
                        "peer_public_key": "public",
                        "peers": peers,
                    }
                ]
            }
        )

    assert exc_info.value.status_code == 400
    assert "too many outbound/peer nodes" in str(exc_info.value.detail)


def test_lab_tester_accepts_endpoint_only_document() -> None:
    ready = _ensure_config_ready(
        {
            "outbounds": [],
            "endpoints": [
                {
                    "type": "wireguard",
                    "tag": "proxy-test",
                    "address": ["172.16.0.2/32"],
                    "private_key": "private",
                    "peers": [
                        {
                            "address": "8.8.8.8",
                            "port": 2408,
                            "public_key": "public",
                            "allowed_ips": ["0.0.0.0/0"],
                        }
                    ],
                }
            ],
        }
    )

    assert ready["route"] == {"final": "proxy-test"}
    assert ready["inbounds"][0]["type"] == "mixed"


def test_lab_ssrf_fallback_fails_closed_on_dns_error(monkeypatch) -> None:
    def fail_resolution(*_args, **_kwargs):
        raise socket.gaierror("resolution failed")

    monkeypatch.setattr(socket, "getaddrinfo", fail_resolution)

    assert _is_private_or_local("unresolvable.example") is True
