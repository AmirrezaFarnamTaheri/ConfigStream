# SPDX-License-Identifier: AGPL-3.0-or-later

from scripts.merge_batches import _proxy_from_dict


def test_proxy_from_dict_skips_chain_artifacts() -> None:
    raw = {
        "config": '{"outbounds":[]}',
        "protocol": "vless",
        "address": "1.1.1.1",
        "port": 443,
        "details": {"is_chain": True},
        "process": "shielded",
    }

    assert _proxy_from_dict(raw) is None


def test_proxy_from_dict_keeps_native_proxy() -> None:
    raw = {
        "config": "vless://123e4567-e89b-12d3-a456-426614174000@example.com:443#node",
        "protocol": "vless",
        "address": "example.com",
        "port": 443,
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "details": {},
        "process": "native",
    }

    proxy = _proxy_from_dict(raw)

    assert proxy is not None
    assert proxy.protocol == "vless"
    assert proxy.process == "native"
