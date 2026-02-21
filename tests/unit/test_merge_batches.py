# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from pathlib import Path

from scripts.merge_batches import _merge_metadata, _proxy_from_dict


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


def test_merge_metadata_aggregates_evasion_and_intelligence(tmp_path: Path) -> None:
    """Verify evasion and intelligence fields are summed across batches."""
    batch1 = tmp_path / "output_batch_1"
    batch2 = tmp_path / "output_batch_2"
    batch1.mkdir()
    batch2.mkdir()

    for d, meta in [
        (
            batch1,
            {
                "fetched_lines": 100,
                "parsed": 80,
                "tested": 70,
                "revived_warp": 2,
                "revived_vwarp": 1,
                "shielded_count": 5,
                "smart_chain_count": 3,
                "evasion_utls_enabled": 10,
                "evasion_dns_safe_count": 15,
            },
        ),
        (
            batch2,
            {
                "fetched_lines": 200,
                "parsed": 150,
                "tested": 140,
                "revived_warp": 2,
                "revived_vwarp": 1,
                "shielded_count": 5,
                "smart_chain_count": 3,
                "evasion_utls_enabled": 10,
                "evasion_dns_safe_count": 15,
            },
        ),
    ]:
        (d / "metadata.json").write_text(
            json.dumps(meta),
            encoding="utf-8",
        )

    result = _merge_metadata([batch1, batch2])

    assert result["fetched_lines"] == 300
    assert result["parsed"] == 230
    assert result["shielded_count"] == 10
    assert result["smart_chain_count"] == 6
    assert result["evasion_utls_enabled"] == 20
    assert result["evasion_dns_safe_count"] == 30
