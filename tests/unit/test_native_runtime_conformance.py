# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for release-authority sing-box connectivity conformance."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from configstream.models import Proxy
from configstream.release_policy import connectivity_check_blocks_release
from configstream.testers import native_conformance
from configstream.testers.native_conformance import (
    MAX_CANDIDATES_PER_PROTOCOL,
    SAMPLES_PER_PROTOCOL,
    conformance_checks,
    eligible_pool_sizes,
    expected_singbox_version,
    run_release_runtime_conformance,
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


def test_select_samples_wider_limit_extends_the_same_deterministic_order() -> None:
    records = [_proxy("trojan", str(index), 10 * index) for index in range(1, 6)]

    narrow = select_samples(records)
    wide = select_samples(records, MAX_CANDIDATES_PER_PROTOCOL)

    assert len(narrow["trojan"]) == SAMPLES_PER_PROTOCOL
    assert len(wide["trojan"]) == 5
    assert [item.id for item in wide["trojan"]][:SAMPLES_PER_PROTOCOL] == [
        item.id for item in narrow["trojan"]
    ]


def test_eligible_pool_sizes_counts_every_working_candidate() -> None:
    records = [
        *[_proxy("trojan", str(index), 10 * index) for index in range(1, 8)],
        _proxy("vless", "9", 5),
        _proxy("vless", "10", 5, working=False),
        _proxy("revived", "11", 1),
        "not-a-record",
    ]

    assert eligible_pool_sizes(records) == {"trojan": 7, "vless": 1}


def _conformance_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "config").mkdir(parents=True)
    (repo_root / "config" / "runtime-versions.json").write_text(
        json.dumps({"sing_box": {"release_validator": "1.14.1"}}),
        encoding="utf-8",
    )
    release_root = tmp_path / "release"
    release_root.mkdir()
    (release_root / "proxies.json").write_text("[]", encoding="utf-8")
    return repo_root


def _stub_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        native_conformance,
        "expected_singbox_version",
        lambda repo_root: "1.14.1",
    )
    monkeypatch.setattr(
        native_conformance,
        "observed_singbox_version",
        lambda binary: "1.14.1",
    )


def test_conformance_retries_beyond_the_first_wave_when_everything_is_dead(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = _conformance_repo(tmp_path)
    release_root = tmp_path / "release"
    records = [_proxy("trojan", str(index), 10 * index) for index in range(1, 6)]
    (release_root / "proxies.json").write_text(json.dumps(records), encoding="utf-8")
    _stub_versions(monkeypatch)
    probed: list[Proxy] = []

    async def recording_probe(tester, protocol, proxy, semaphore):
        del tester, semaphore
        probed.append(proxy)
        # The fastest representatives are dead; a later candidate still works.
        if proxy.latency is not None and proxy.latency <= 30:
            return protocol, False, "probe_failed"
        return protocol, True, None

    monkeypatch.setattr(native_conformance, "_probe", recording_probe)

    report = asyncio.run(
        run_release_runtime_conformance(
            release_root,
            singbox_binary=tmp_path / "sing-box",
            repo_root=repo_root,
        )
    )

    assert report["status"] == "passed"
    assert report["protocols"]["trojan"]["attempted"] == 5
    assert report["protocols"]["trojan"]["passed"] == 2
    assert report["protocols"]["trojan"]["status"] == "passed"
    latencies = [proxy.latency for proxy in probed]
    assert all(latency is not None for latency in latencies)
    assert sorted(latency for latency in latencies if latency is not None) == [
        10,
        20,
        30,
        40,
        50,
    ]


def test_conformance_fails_only_after_the_bounded_candidate_pool_is_exhausted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = _conformance_repo(tmp_path)
    release_root = tmp_path / "release"
    records = [_proxy("trojan", str(index), 10 * index) for index in range(1, 8)]
    (release_root / "proxies.json").write_text(json.dumps(records), encoding="utf-8")
    _stub_versions(monkeypatch)
    probed: list[Proxy] = []

    async def always_dead(tester, protocol, proxy, semaphore):
        del tester, semaphore
        probed.append(proxy)
        return protocol, False, "probe_failed"

    monkeypatch.setattr(native_conformance, "_probe", always_dead)

    report = asyncio.run(
        run_release_runtime_conformance(
            release_root,
            singbox_binary=tmp_path / "sing-box",
            repo_root=repo_root,
        )
    )

    assert report["status"] == "failed"
    assert report["protocols"]["trojan"]["attempted"] == MAX_CANDIDATES_PER_PROTOCOL
    assert report["protocols"]["trojan"]["passed"] == 0
    assert report["error"] == "release sing-box connectivity failed for: trojan"
    assert len(probed) == MAX_CANDIDATES_PER_PROTOCOL


def test_conformance_does_not_retry_protocols_that_already_passed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = _conformance_repo(tmp_path)
    release_root = tmp_path / "release"
    records = [
        *[_proxy("trojan", str(index), 10 * index) for index in range(1, 6)],
        _proxy("socks5", "9", 5),
    ]
    (release_root / "proxies.json").write_text(json.dumps(records), encoding="utf-8")
    _stub_versions(monkeypatch)
    probed: list[tuple[str, int | None]] = []

    async def socks_only(tester, protocol, proxy, semaphore):
        del tester, semaphore
        probed.append((protocol, proxy.latency))
        if protocol == "socks5":
            return protocol, True, None
        return protocol, False, "probe_failed"

    monkeypatch.setattr(native_conformance, "_probe", socks_only)

    report = asyncio.run(
        run_release_runtime_conformance(
            release_root,
            singbox_binary=tmp_path / "sing-box",
            repo_root=repo_root,
        )
    )

    assert report["protocols"]["socks5"] == {
        "status": "passed",
        "attempted": 1,
        "passed": 1,
        "eligible_candidates": 1,
        "errors": [],
    }
    assert [latency for protocol, latency in probed if protocol == "socks5"] == [5]


def test_conformance_reports_the_full_eligible_pool_per_protocol(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The gate needs the true pool size, not just the sampled window."""
    repo_root = _conformance_repo(tmp_path)
    release_root = tmp_path / "release"
    records = [_proxy("trojan", str(index), 10 * index) for index in range(1, 6)]
    (release_root / "proxies.json").write_text(json.dumps(records), encoding="utf-8")
    _stub_versions(monkeypatch)

    async def always_dead(tester, protocol, proxy, semaphore):
        del tester, semaphore
        return protocol, False, "probe_failed"

    monkeypatch.setattr(native_conformance, "_probe", always_dead)

    report = asyncio.run(
        run_release_runtime_conformance(
            release_root,
            singbox_binary=tmp_path / "sing-box",
            repo_root=repo_root,
        )
    )

    trojan = report["protocols"]["trojan"]
    assert trojan["eligible_candidates"] == 5
    assert trojan["attempted"] == 5


def test_conformance_checks_carry_exhaustion_evidence_to_the_gate() -> None:
    checks = conformance_checks(
        {
            "status": "failed",
            "error": "release sing-box connectivity failed for: trojan",
            "protocols": {
                "trojan": {
                    "status": "failed",
                    "attempted": 5,
                    "passed": 0,
                    "eligible_candidates": 5,
                }
            },
        },
        proxies_digest="c" * 64,
        binary_digest="d" * 64,
    )

    assert checks == [
        {
            "core": "sing-box-connectivity:trojan",
            "path": "proxies.json",
            "status": "failed",
            "command": ["sing-box", "release-runtime-connectivity", "trojan"],
            "artifact_sha256": "c" * 64,
            "binary_sha256": "d" * 64,
            "error": "release sing-box connectivity failed for: trojan",
            "attempted": 5,
            "eligible_candidates": 5,
        }
    ]
    # The exhausted, fully evidenced probe is an availability observation.
    assert connectivity_check_blocks_release(checks[0]) is False


def test_expected_version_comes_from_release_authority_contract(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "runtime-versions.json").write_text(
        json.dumps({"sing_box": {"release_validator": "1.14.1"}}),
        encoding="utf-8",
    )

    assert expected_singbox_version(tmp_path) == "1.14.1"


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
