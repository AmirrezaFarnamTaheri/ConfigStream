# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from configstream.models import Proxy
from configstream.testers.manager import SingBoxTester, _record_revived_go_health
from scripts.reconcile_release_metadata import reconcile
from scripts.shard_sources import active_source_lines, load_quarantined_sources


def _revived_proxy(index: int) -> Proxy:
    return Proxy(
        config=f"revived://{index}",
        protocol="revived",
        address=f"203.0.113.{index + 1}",
        port=443,
        details={
            "chain_outbounds": [
                {
                    "type": "socks",
                    "tag": f"hop-{index}",
                    "server": "proxy.example",
                    "server_port": 1080,
                }
            ]
        },
    )


def test_runtime_quarantine_excludes_listed_sources(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    batch = sources / "batch_1.txt"
    batch.write_text(
        "# header\nhttps://active.example/sub\nhttps://dead.example/sub\n",
        encoding="utf-8",
    )
    (sources / "quarantine.txt").write_text(
        "# evidence\nhttps://dead.example/sub\n",
        encoding="utf-8",
    )

    quarantined = load_quarantined_sources(sources)

    assert quarantined == {"https://dead.example/sub"}
    assert active_source_lines(batch, quarantined) == ["https://active.example/sub"]


def test_reconcile_removes_duplicate_failure_summary_and_repairs_audit(
    tmp_path: Path,
) -> None:
    root = tmp_path / "output"
    root.mkdir()
    (root / "proxies.json").write_text("[]\n", encoding="utf-8")
    metadata = {
        "shielded_count": 0,
        "shielded_candidate_count": 0,
        "source_failure_summary": {"total": 287},
        "time_limited": True,
        "fetched_sources": 2012,
        "total_configured_sources": 1009,
        "pipeline_execution_audit": {
            "fetched_sources": 2012,
            "total_sources": 1009,
            "source_toxicity_rate": 2900.6461,
            "time_limited": False,
        },
        "shard_summary": {
            "covered_sources": 722,
            "configured_sources": 1027,
            "source_attempts": 1009,
            "source_failures": {"total": 287},
            "time_limited": 2,
        },
    }
    (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    reconcile(root)

    reconciled = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert "source_failure_summary" not in reconciled
    assert reconciled["shard_summary"]["source_failures"] == {"total": 287}
    audit = reconciled["pipeline_execution_audit"]
    assert audit["fetched_sources"] == 722
    assert audit["total_sources"] == 1027
    assert audit["source_toxicity_rate"] == pytest.approx((287 / 1009) * 100.0)
    assert audit["time_limited"] is True


def test_revived_go_health_trips_after_five_incomplete_results() -> None:
    tester: Any = object.__new__(SingBoxTester)
    tester._revived_go_failures = 0
    tester._revived_go_failure_limit = 5
    tester._revived_go_disabled = False

    for _ in range(4):
        _record_revived_go_health(tester, 1)
        assert tester._revived_go_disabled is False

    _record_revived_go_health(tester, 1)
    assert tester._revived_go_disabled is True

    tester._revived_go_failures = 3
    tester._revived_go_disabled = False
    _record_revived_go_health(tester, 0)
    assert tester._revived_go_failures == 0
    assert tester._revived_go_disabled is False


@pytest.mark.asyncio
async def test_revived_python_fallback_respects_existing_batch_budget() -> None:
    class FakeGoTester:
        available = True

        async def test_custom_configs(self, configs, check_honeypot=False):
            return {}

        async def test_batch(self, proxies, check_honeypot=False):
            return proxies

    class FakePythonTester:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def test_via_singbox(self, proxy: Proxy) -> Proxy:
            self.calls.append(proxy.id)
            proxy.is_working = True
            return proxy

    tester: Any = object.__new__(SingBoxTester)
    tester.timeout = 1.0
    tester.cache = None
    tester.strict_security = False
    tester.settings = SimpleNamespace(PY_TESTER_BATCH_SIZE=2)
    tester.dry_run = False
    tester.max_workers = 2
    tester.go_tester = FakeGoTester()
    python_tester = FakePythonTester()
    tester._python_tester = python_tester
    tester._revived_go_failures = 0
    tester._revived_go_failure_limit = 5
    tester._revived_go_disabled = False

    proxies = [_revived_proxy(index) for index in range(5)]
    await tester.test_batch(proxies)

    assert len(python_tester.calls) == 2
    skipped = [
        proxy
        for proxy in proxies
        if proxy.details.get("error") == "REVIVAL_FALLBACK_BUDGET_EXHAUSTED"
    ]
    assert len(skipped) == 3
    assert all(proxy.is_working is False for proxy in skipped)
