# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from configstream.dns_profiles import build_singbox_dns_profile
from configstream.generators.singbox import SingBoxGenerator
from configstream.generators.split import generate_split_outputs
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
            }
        ],
        "dns": {
            "servers": [
                {
                    "type": "udp",
                    "tag": "local_local",
                    "server": "1.1.1.1",
                    "server_port": 53,
                },
                {
                    "type": "udp",
                    "tag": "backup_dns",
                    "server": "8.8.8.8",
                    "server_port": 53,
                },
            ]
        },
        "route": {"final": "proxy", "rules": []},
    }

    errors = validate_singbox_config(payload, "singbox.json")

    assert any("outbounds[0] domain dial lacks domain resolver" in error for error in errors)


def test_singbox_contract_rejects_direct_outbound_without_resolver() -> None:
    payload = {
        "outbounds": [{"type": "direct", "tag": "direct"}],
        "dns": {
            "servers": [
                {
                    "type": "udp",
                    "tag": "local_local",
                    "server": "1.1.1.1",
                    "server_port": 53,
                },
                {
                    "type": "udp",
                    "tag": "backup_dns",
                    "server": "8.8.8.8",
                    "server_port": 53,
                },
            ]
        },
        "route": {"final": "direct", "rules": []},
    }

    errors = validate_singbox_config(payload, "singbox.json")

    assert any("outbounds[0] domain dial lacks domain resolver" in error for error in errors)


def test_singbox_contract_allows_implicit_single_dns_resolver() -> None:
    payload = {
        "outbounds": [{"type": "direct", "tag": "direct"}],
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
        "route": {"final": "direct", "rules": []},
    }

    assert validate_singbox_config(payload, "singbox.json") == []


def test_singbox_contract_allows_no_dns_configuration() -> None:
    payload = {
        "outbounds": [{"type": "direct", "tag": "direct"}],
        "route": {"final": "direct", "rules": []},
    }

    assert validate_singbox_config(payload, "singbox.json") == []


def test_split_configs_set_resolver_for_multi_dns_profile(tmp_path: Path) -> None:
    files = generate_split_outputs(
        [], tmp_path, singbox_dns_profile=build_singbox_dns_profile()
    )

    for key in ("singbox", "singbox_vpn"):
        payload = json.loads(files[key].read_text(encoding="utf-8"))
        assert payload["route"]["default_domain_resolver"] == "local_local"


def test_unverified_shielded_candidate_note_is_not_release_blocking() -> None:
    assert _is_nonblocking_health_note("unverified_shielded_candidates:15")
    assert not _is_nonblocking_health_note("pipeline_time_limited")
