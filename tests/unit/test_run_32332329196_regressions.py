# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from configstream.generators.singbox import SingBoxGenerator
from configstream.output.singbox_contract import validate_singbox_config
from scripts.aggregate_shard_health import bounded_source_counts
from scripts.release_gate import _is_nonblocking_health_note


def test_source_attempts_do_not_inflate_coverage() -> None:
    assert bounded_source_counts(source_count=9, fetched_sources=102) == (9, 102)
    assert bounded_source_counts(source_count=9, fetched_sources=7) == (7, 7)


def test_singbox_generator_supplies_resolver_for_hostname_dials() -> None:
    config = SingBoxGenerator().generate(
        [],
        extra_outbounds=[
            {
                "type": "socks",
                "tag": "proxy",
                "server": "proxy.example",
                "server_port": 1080,
            }
        ],
    )

    assert config["route"]["default_domain_resolver"] == "local_local"
    dns_servers = {item["tag"]: item for item in config["dns"]["servers"]}
    assert dns_servers["remote_dns"]["domain_resolver"] == "local_local"
    assert validate_singbox_config(config, "singbox.json") == []


def test_singbox_contract_rejects_hostname_dial_without_resolver() -> None:
    payload = {
        "outbounds": [
            {
                "type": "socks",
                "tag": "proxy",
                "server": "proxy.example",
                "server_port": 1080,
            },
            {"type": "direct", "tag": "direct"},
        ],
        "dns": {
            "servers": [
                {
                    "type": "udp",
                    "tag": "local_local",
                    "server": "1.1.1.1",
                    "server_port": 53,
                }
            ]
        },
        "route": {"final": "proxy", "rules": []},
    }

    errors = validate_singbox_config(payload, "singbox.json")

    assert any("hostname dial lacks domain resolver" in error for error in errors)


def test_unverified_shielded_candidate_note_is_not_release_blocking() -> None:
    assert _is_nonblocking_health_note("unverified_shielded_candidates:15")
    assert not _is_nonblocking_health_note("pipeline_time_limited")
