# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path

import pytest

from configstream.history.tracker import ProxyHistoryTracker
from configstream.intelligence.washer.core import ProxyWasher
from configstream.models import Proxy
from configstream.output_handler import _chain_to_proxy_entry, generate_pipeline_outputs
from configstream.pipeline_stats import PipelineStats


@pytest.mark.asyncio
async def test_generate_pipeline_outputs_creates_frontend_data_files(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = PipelineStats()
    history = ProxyHistoryTracker(tmp_path / "history.db")
    washer = ProxyWasher("[]")
    washer.clean_ips = [("162.159.192.1", 2408), ("162.159.193.5", 2408)]

    try:
        await generate_pipeline_outputs([], out_dir, stats, history, washer=washer)
    finally:
        history.close()

    # Required for lab.html auto-discovery
    clean_ips_path = out_dir / "data" / "clean_ips.json"
    assert clean_ips_path.exists()
    clean_ips = json.loads(clean_ips_path.read_text(encoding="utf-8"))
    assert isinstance(clean_ips, list)
    assert clean_ips and clean_ips[0]["ip"] == "162.159.192.1"

    # Required for analytics/dashboard pages
    assert (out_dir / "data" / "proxy_history_viz.json").exists()
    assert (out_dir / "data" / "active_proxy_trend.json").exists()
    assert (out_dir / "data" / "evasion_trend.json").exists()

    # Canonical stats source for the frontend
    assert (out_dir / "metadata.json").exists()


@pytest.mark.asyncio
async def test_generate_pipeline_outputs_preserves_revived_process_and_dns_flags(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    native = Proxy(
        config="vless://123e4567-e89b-12d3-a456-426614174000@alpha.example:443?security=tls&sni=alpha.example#native",
        protocol="vless",
        address="alpha.example",
        port=443,
        uuid="123e4567-e89b-12d3-a456-426614174000",
        process="native",
        is_working=True,
        resolved_ip="1.1.1.1",
        details={"sni": "alpha.example"},
    )
    revived = Proxy(
        config="revived://beta.example",
        protocol="revived",
        address="beta.example",
        port=8443,
        uuid="revived-test",
        process="revived-vwarp",
        is_working=False,
        resolved_ip="1.0.0.1",
        details={
            "is_revived": True,
            "origin_config": {
                "protocol": "vless",
                "address": "beta.example",
                "port": 8443,
                "uuid": "revived-test",
                "resolved_ip": "1.0.0.1",
                "details": {"security": "tls", "sni": "beta.example"},
            },
        },
    )

    stats = PipelineStats()
    history = ProxyHistoryTracker(tmp_path / "history.db")
    washer = ProxyWasher("[]")
    washer.clean_ips = [("162.159.192.1", 2408)]

    try:
        await generate_pipeline_outputs(
            [native, revived], out_dir, stats, history, washer=washer
        )
    finally:
        history.close()

    proxies = json.loads((out_dir / "proxies.json").read_text(encoding="utf-8"))
    revived_rows = json.loads((out_dir / "revived.json").read_text(encoding="utf-8"))
    dns_safe_rows = json.loads(
        (out_dir / "proxies-dns-safe.json").read_text(encoding="utf-8")
    )
    revived_dns_safe_rows = json.loads(
        (out_dir / "revived-dns-safe.json").read_text(encoding="utf-8")
    )

    revived_in_proxies = [row for row in proxies if row.get("id") == "revived-test"]
    assert revived_in_proxies
    assert revived_in_proxies[0].get("process") == "revived-vwarp"

    assert revived_rows
    assert all(
        str(row.get("process", "")).startswith("revived") for row in revived_rows
    )
    assert all(
        (row.get("details") or {}).get("dns_safe") is True for row in dns_safe_rows
    )
    assert all(
        (row.get("details") or {}).get("dns_safe") is True
        for row in revived_dns_safe_rows
    )


def test_shielded_chain_entries_are_candidates_not_working() -> None:
    chain = [
        {
            "type": "vless",
            "tag": "origin",
            "server": "origin.example",
            "server_port": 443,
        },
        {
            "type": "wireguard",
            "tag": "GOLD-origin",
            "server": "162.159.192.1",
            "server_port": 2408,
            "detour": "origin",
            "_is_shielded": True,
        },
    ]

    row = _chain_to_proxy_entry(chain, process="shielded")

    assert row["is_working"] is False
    assert row["process"] == "shielded"
    assert "candidate" in row["tags"]
    assert row["details"]["shielded_candidate"] is True
    assert row["details"]["shielded_verified"] is False
