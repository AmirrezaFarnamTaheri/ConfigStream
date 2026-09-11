# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail-closed regression coverage for live-lab capability-bearing fields."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from configstream.lab_validation import _validate_and_build_lab_config


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("certificate_path", "/etc/passwd"),
        ("client_key_path", "/tmp/client.key"),
        ("config_path", "/proc/self/environ"),
        ("bind_interface", "eth0"),
        ("routing_mark", 1234),
        ("netns", "/var/run/netns/host"),
    ],
)
async def test_lab_rejects_host_capability_fields(field: str, value: object) -> None:
    config = {"outbounds": [{"type": "direct", field: value}]}

    with pytest.raises(HTTPException) as exc_info:
        await _validate_and_build_lab_config(config)

    assert exc_info.value.status_code == 400
    assert field in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_lab_rejects_nested_tls_path_capability() -> None:
    config = {
        "outbounds": [
            {
                "type": "direct",
                "tls": {"enabled": True, "client_certificate_path": "/tmp/cert.pem"},
            }
        ]
    }

    with pytest.raises(HTTPException) as exc_info:
        await _validate_and_build_lab_config(config)

    assert exc_info.value.status_code == 400
    assert "client_certificate_path" in str(exc_info.value.detail)
