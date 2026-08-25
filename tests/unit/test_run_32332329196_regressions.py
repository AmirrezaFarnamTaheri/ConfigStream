# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from configstream.dns_profiles import build_singbox_dns_profile
from configstream.generators.singbox import SingBoxGenerator
from configstream.generators.split import generate_split_outputs
from configstream.output.singbox_contract import validate_singbox_config
from scripts.aggregate_shard_health import (
    bounded_source_counts,
    classify_fetch_failure,
    fetch_failure_counts,
    fetch_summary_counts,
)
from scripts.release_gate import _is_nonblocking_health_note


def test_source_attempts_do_not_inflate_coverage() -> None:
    """Keep consumer observations from inflating unique source coverage."""

    assert bounded_source_counts(source_count=9, fetched_sources=102) == (9, 102)
    assert bounded_source_counts(source_count=9, fetched_sources=7) == (7, 7)


def test_fetch_summary_uses_unique_source_success_counts(tmp_path: Path) -> None:
    """Prefer producer success counts over downstream queue observations."""

    log = tmp_path / "pipeline_batch_10_part_2.log"
    log.write_text(
        "Fetch Summary: 11/12 sources successful.\n",
        encoding="utf-8",
    )

    assert fetch_summary_counts(log, source_count=12, fallback_fetched_sources=28) == (
        11,
        12,
    )


def test_fetch_summary_falls_back_when_log_has_no_summary(tmp_path: Path) -> None:
    """Use bounded legacy counters when a producer summary is unavailable."""

    log = tmp_path / "pipeline_batch_10_part_2.log"
    log.write_text("no summary\n", encoding="utf-8")

    assert fetch_summary_counts(log, source_count=12, fallback_fetched_sources=28) == (
        12,
        28,
    )


def test_source_failure_diagnostics_classify_host_and_failure_type(
    tmp_path: Path,
) -> None:
    """Classify source failures and aggregate them by logical host."""

    log = tmp_path / "pipeline_batch_9_part_5.log"
    log.write_text(
        "\n".join(
            [
                "Failed: https://raw.githubusercontent.com/a/b/main/x - Max retries exceeded: DNS rebinding detected for 'raw.githubusercontent.com' (Status: 0)",
                "Failed: https://raw.githubusercontent.com/a/b/main/y - Max retries exceeded: All connection attempts failed (Status: 0)",
                "Failed: https://example.com/missing - Permanent Error: 404 (Status: 404)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = fetch_failure_counts(log)

    assert summary["total"] == 3
    assert summary["by_category"] == {
        "dns_rebinding": 1,
        "connect_error": 1,
        "permanent_http": 1,
    }
    assert summary["by_host"] == {
        "raw.githubusercontent.com": 2,
        "example.com": 1,
    }
    assert summary["by_host_category"]["raw.githubusercontent.com:dns_rebinding"] == 1
    assert classify_fetch_failure("request timed out") == "timeout"
    assert classify_fetch_failure("Rate limited", 429) == "rate_limited"


def test_source_failure_diagnostics_parse_rich_wrapped_producer_logs(
    tmp_path: Path,
) -> None:
    """Reconstruct Rich-wrapped producer warnings before classification."""

    log = tmp_path / "pipeline_batch_9_part_5.log"
    log.write_text(
        "\n".join(
            [
                "           WARNING  Failed to fetch https://buyproxy.ru/free:    producer.py:580",
                "                    Max retries exceeded: Server disconnected",
                "                    without sending a response. (Status: 0)",
                "           WARNING  Failed to fetch                              producer.py:580",
                "                    https://raw.githubusercontent.com/v2clash/V2",
                "                    ray/main/list.txt: Max retries exceeded: DNS",
                "                    rebinding detected for",
                "                    'raw.githubusercontent.com' (Status: 0)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = fetch_failure_counts(log)

    assert summary["total"] == 2
    assert summary["by_category"] == {"connect_error": 1, "dns_rebinding": 1}
    assert summary["by_host"] == {
        "buyproxy.ru": 1,
        "raw.githubusercontent.com": 1,
    }
    assert summary["by_host_category"] == {
        "buyproxy.ru:connect_error": 1,
        "raw.githubusercontent.com:dns_rebinding": 1,
    }


def test_source_failure_diagnostics_use_canonical_tie_order(tmp_path: Path) -> None:
    """Serialize tied failure counts in stable lexical order."""

    log = tmp_path / "pipeline_batch_9_part_5.log"
    log.write_text(
        "\n".join(
            [
                "Failed: https://z.example/a - Max retries exceeded: DNS rebinding detected for 'z.example' (Status: 0)",
                "Failed: https://a.example/b - Max retries exceeded: All connection attempts failed (Status: 0)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = fetch_failure_counts(log)

    assert list(summary["by_category"]) == ["connect_error", "dns_rebinding"]
    assert list(summary["by_host"]) == ["a.example", "z.example"]
    assert list(summary["by_host_category"]) == [
        "a.example:connect_error",
        "z.example:dns_rebinding",
    ]


def test_singbox_generator_supplies_resolver_for_hostname_dials() -> None:
    """Supply a default resolver when generated outbounds dial hostnames."""

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
    """Reject hostname dial outbounds when multi-DNS routing lacks a resolver."""

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

    assert any(
        "outbounds[0] domain dial lacks domain resolver" in error for error in errors
    )


def test_singbox_contract_rejects_direct_outbound_without_resolver() -> None:
    """Reject direct hostname routing when multiple DNS servers are ambiguous."""

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

    assert any(
        "outbounds[0] domain dial lacks domain resolver" in error for error in errors
    )


def test_singbox_contract_allows_implicit_single_dns_resolver() -> None:
    """Allow implicit resolution when exactly one DNS server is configured."""

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
    """Allow direct routing when the configuration defines no DNS section."""

    payload = {
        "outbounds": [{"type": "direct", "tag": "direct"}],
        "route": {"final": "direct", "rules": []},
    }

    assert validate_singbox_config(payload, "singbox.json") == []


def test_split_configs_set_resolver_for_multi_dns_profile(tmp_path: Path) -> None:
    """Set the default resolver in split outputs that use multiple DNS servers."""

    files = generate_split_outputs(
        [], tmp_path, singbox_dns_profile=build_singbox_dns_profile()
    )

    for key in ("singbox", "singbox_vpn"):
        payload = json.loads(files[key].read_text(encoding="utf-8"))
        assert payload["route"]["default_domain_resolver"] == "local_local"


def test_unverified_shielded_candidate_note_is_not_release_blocking() -> None:
    """Treat unverified shielded candidates as a health note, not a blocker."""

    assert _is_nonblocking_health_note("unverified_shielded_candidates:15")


def test_time_limited_intake_is_a_health_note_not_a_blocker() -> None:
    """A time-limited intake means slower coverage, not bad proxies.

    Runs 32668367033 / 32722445848 / 32754492501 each failed solely on
    ``pipeline_time_limited`` while passing every other gate (contracts,
    native clients, coverage) - with a different shard hitting the window
    each time, so no fixed batch limit can prevent it structurally.
    """

    assert _is_nonblocking_health_note("pipeline_time_limited")
