# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.history.tracker import ProxyHistoryTracker
from configstream.intelligence.washer.core import ProxyWasher
from configstream.models import Proxy
from configstream.output_handler import (
    _verify_shielded_candidates,
    generate_pipeline_outputs,
)
from configstream.pipeline_stats import PipelineStats


def _failed_proxy() -> Proxy:
    return Proxy(
        config="vless://123e4567-e89b-12d3-a456-426614174000@dead.example:443",
        protocol="vless",
        address="dead.example",
        port=443,
        uuid="123e4567-e89b-12d3-a456-426614174000",
        is_working=False,
    )


def _shielded_outbounds() -> list[dict[str, object]]:
    return [
        {
            "type": "wireguard",
            "tag": "SHIELD-XX-0",
            "server": "162.159.192.1",
            "server_port": 2408,
            "_process": "shield_base",
        },
        {
            "type": "vless",
            "tag": "dead-shielded",
            "server": "dead.example",
            "server_port": 443,
            "detour": "SHIELD-XX-0",
            "_process": "shield_payload",
            "_is_shielded": True,
        },
    ]


async def _generate(
    tmp_path: Path, *, tester: Any
) -> tuple[list[dict[str, Any]], PipelineStats]:
    failed = _failed_proxy()
    outbounds = _shielded_outbounds()
    candidate = Proxy(
        config="chain://",
        protocol="revived",
        address="dead.example",
        port=443,
        process="shielded",
        details={"chain": outbounds, "is_revived": True},
        is_working=False,
    )
    washer = MagicMock()
    washer.clean_ips = []
    washer.wash_batch.return_value = ([], set(), {})
    washer.shield_batch.return_value = (outbounds, {failed.id})
    washer.create_revived_proxy.return_value = candidate

    stats = PipelineStats()
    history = ProxyHistoryTracker(tmp_path / "history.db")
    output = tmp_path / "output"
    output.mkdir()
    try:
        with (
            patch(
                "configstream.output_handler.generate_categorized_outputs",
                return_value={},
            ),
            patch("configstream.output_handler.generate_smart_chains", return_value={}),
            patch("configstream.output_handler.write_public_artifact_contract"),
        ):
            await generate_pipeline_outputs(
                [failed], output, stats, history, washer=washer, tester=tester
            )
    finally:
        history.close()
    return json.loads((output / "proxies.json").read_text(encoding="utf-8")), stats


@pytest.mark.asyncio
async def test_failed_shielded_verification_preserves_one_public_candidate(
    tmp_path: Path,
) -> None:
    tester = MagicMock()

    async def fail_verification(proxies: list[Proxy]) -> list[Proxy]:
        proxies[0].details["error"] = "REVIVAL_FAILED"
        return proxies

    tester.test_batch = AsyncMock(side_effect=fail_verification)
    rows, stats = await _generate(tmp_path, tester=tester)

    shielded = [row for row in rows if row.get("process") == "shielded"]
    assert len(shielded) == 1
    assert shielded[0]["is_working"] is False
    assert shielded[0]["details"]["shielded_candidate"] is True
    assert shielded[0]["details"]["shielded_verified"] is False
    assert shielded[0]["details"]["error"] == "REVIVAL_FAILED"
    assert stats.shielded_candidate_count == 1
    assert stats.shielded_verified_count == 0
    assert sum(bool(row.get("is_working")) for row in rows) == 0


@pytest.mark.asyncio
async def test_successful_shielded_verification_marks_same_public_record_verified(
    tmp_path: Path,
) -> None:
    tester = MagicMock()

    async def pass_verification(proxies: list[Proxy]) -> list[Proxy]:
        proxies[0].is_working = True
        return proxies

    tester.test_batch = AsyncMock(side_effect=pass_verification)
    rows, stats = await _generate(tmp_path, tester=tester)

    shielded = [row for row in rows if row.get("process") == "shielded"]
    assert len(shielded) == 1
    assert shielded[0]["is_working"] is True
    assert shielded[0]["details"]["shielded_candidate"] is True
    assert shielded[0]["details"]["shielded_verified"] is True
    assert stats.shielded_candidate_count == 1
    assert stats.shielded_verified_count == 1
    assert sum(bool(row.get("is_working")) for row in rows) == 1


@pytest.mark.asyncio
async def test_shielded_verifier_exception_fails_closed_but_keeps_candidate(
    tmp_path: Path,
) -> None:
    tester = MagicMock()
    tester.test_batch = AsyncMock(side_effect=RuntimeError("tester unavailable"))

    rows, stats = await _generate(tmp_path, tester=tester)

    shielded = [row for row in rows if row.get("process") == "shielded"]
    assert len(shielded) == 1
    assert shielded[0]["is_working"] is False
    assert shielded[0]["details"]["shielded_candidate"] is True
    assert shielded[0]["details"]["shielded_verified"] is False
    assert stats.shielded_candidate_count == 1
    assert stats.shielded_verified_count == 0


@pytest.mark.asyncio
async def test_colliding_endpoint_ids_keep_independent_verification_results() -> None:
    first = Proxy(
        config="chain://a",
        protocol="revived",
        address="shared.example",
        port=443,
        details={"is_revived": True, "chain": [{"tag": "a"}]},
    )
    second = first.model_copy(deep=True)
    second.config = "chain://b"
    second.details["chain"] = [{"tag": "b"}]
    assert first.id == second.id

    async def verify(proxies: list[Proxy]) -> list[Proxy]:
        results = [proxy.model_copy(deep=True) for proxy in proxies]
        results[0].is_working = True
        results[1].is_working = False
        return results

    tester = MagicMock()
    tester.test_batch = AsyncMock(side_effect=verify)
    stats = PipelineStats()
    results = await _verify_shielded_candidates([first, second], tester, stats)

    assert results[0] is not first
    assert results[1] is not second
    assert [result.is_working for result in results] == [True, False]
    assert results[0].details["chain"] == [{"tag": "a"}]
    assert results[1].details["chain"] == [{"tag": "b"}]
    assert stats.shielded_verified_count == 1


@pytest.mark.asyncio
async def test_mismatched_or_missing_shielded_results_fail_closed() -> None:
    first = Proxy(
        config="chain://first",
        protocol="revived",
        address="first.example",
        port=443,
        details={"is_revived": True, "chain": [{"tag": "first"}]},
    )
    second = Proxy(
        config="chain://second",
        protocol="revived",
        address="second.example",
        port=443,
        details={"is_revived": True, "chain": [{"tag": "second"}]},
    )

    async def verify(_proxies: list[Proxy]) -> list[Proxy]:
        mismatched = second.model_copy(deep=True)
        mismatched.is_working = True
        return [mismatched]

    tester = MagicMock()
    tester.test_batch = AsyncMock(side_effect=verify)
    stats = PipelineStats()
    results = await _verify_shielded_candidates([first, second], tester, stats)

    assert results == [first, second]
    assert all(result.is_working is False for result in results)
    assert stats.shielded_verified_count == 0


def test_revived_chain_fingerprint_makes_same_endpoint_ids_distinct() -> None:
    entry = {"type": "wireguard", "tag": "shield", "server": "1.1.1.1"}
    first = ProxyWasher.create_revived_proxy(
        MagicMock(),
        entry,
        {
            "type": "vless",
            "tag": "first",
            "server": "shared.example",
            "server_port": 443,
        },
        "shielded",
    )
    second = ProxyWasher.create_revived_proxy(
        MagicMock(),
        entry,
        {
            "type": "vless",
            "tag": "second",
            "server": "shared.example",
            "server_port": 443,
        },
        "shielded",
    )

    assert first.details["chain_fingerprint"] != second.details["chain_fingerprint"]
    assert first.id != second.id


@pytest.mark.asyncio
async def test_dns_hardened_pool_contains_late_shielded_candidates(
    tmp_path: Path,
) -> None:
    rows, stats = await _generate(tmp_path, tester=None)
    hardened = json.loads(
        (tmp_path / "output" / "proxies-dns-hardened.json").read_text(encoding="utf-8")
    )
    assert any(row.get("process") == "shielded" for row in hardened)
    assert stats.evasion_dns_hardened_count == len(hardened)
