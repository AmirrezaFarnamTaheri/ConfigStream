# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for release-authority sing-box connectivity conformance."""

from __future__ import annotations

import json
from pathlib import Path

from configstream.testers.native_conformance import (
    conformance_checks,
    expected_singbox_version,
    select_samples,
)


def _proxy(protocol: str, suffix: str, latency: float, *, working: bool = True) -> dict:
    return {
        "config": f"{protocol}://example-{suffix}",
        "protocol": protocol,
        "address": f"203.0.113.{int(suffix)}",
        "port": 443,
        "uuid": f"00000000-0000-4000-8000-{int(suffix):012d}",
        "latency": latency,
        "is_working": working,
    }


def test_select_samples_is_bounded_deterministic_and_working_only() -> None:
    records = [
        _proxy("vmess", "1", 90),
        _proxy("vmess", "2", 10),
        _proxy("vmess", "3", 30),
        _proxy("vmess", "4", 20),
        _proxy("vless", "5", 15),
        _proxy("vless", "6", 5, working=False),
        _proxy("revived", "7", 1),
    ]

    selected = select_samples(records)

    assert list(selected) == ["vless", "vmess"]
    assert [item.latency for item in selected["vmess"]] == [10, 20, 30]
    assert [item.latency for item in selected["vless"]] == [15]


def test_expected_version_comes_from_release_authority_contract(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "runtime-versions.json").write_text(
        json.dumps({"sing_box": {"release_validator": "1.13.18"}}),
        encoding="utf-8",
    )

    assert expected_singbox_version(tmp_path) == "1.13.18"


def test_conformance_checks_fail_closed_when_probe_evidence_is_missing() -> None:
    checks = conformance_checks(
        {"status": "failed", "protocols": {}, "error": "version mismatch"},
        proxies_digest="a" * 64,
        binary_digest="b" * 64,
    )

    assert checks == [
        {
            "core": "sing-box-connectivity",
            "path": "proxies.json",
            "status": "failed",
            "command": ["sing-box", "release-runtime-connectivity"],
            "artifact_sha256": "a" * 64,
            "binary_sha256": "b" * 64,
            "error": "version mismatch",
        }
    ]


def test_conformance_checks_are_enforced_per_protocol() -> None:
    checks = conformance_checks(
        {
            "status": "failed",
            "error": "release sing-box connectivity failed for: vmess",
            "protocols": {
                "vless": {"status": "passed", "attempted": 2, "passed": 1},
                "vmess": {"status": "failed", "attempted": 3, "passed": 0},
            },
        },
        proxies_digest="c" * 64,
        binary_digest="d" * 64,
    )

    by_core = {item["core"]: item for item in checks}
    assert by_core["sing-box-connectivity:vless"]["status"] == "passed"
    assert by_core["sing-box-connectivity:vmess"]["status"] == "failed"
    assert by_core["sing-box-connectivity:vmess"]["path"] == "proxies.json"
