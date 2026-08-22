# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from configstream.models import Proxy
from configstream.testers.manager import SingBoxTester, _record_revived_go_health
from scripts import shard_sources
from scripts.reconcile_release_metadata import _reconcile_execution_audit, reconcile
from scripts.shard_sources import active_source_lines, load_quarantined_sources


def _revived_proxy(index: int) -> Proxy:
    """Build a revived proxy fixture with chain-outbound details."""

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
    """Runtime sharding should skip locators listed in the quarantine file."""

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
    """Reconciliation should drop duplicate source failures and repair audit counters."""

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


def test_reconcile_execution_audit_preserves_explicit_zero_counts() -> None:
    """Zero-valued shard counters must override stale aggregate metadata."""

    metadata: dict[str, Any] = {
        "fetched_sources": 722,
        "total_configured_sources": 1027,
        "pipeline_execution_audit": {
            "fetched_sources": 722,
            "total_sources": 1027,
            "source_toxicity_rate": 1.0,
            "time_limited": True,
        },
        "shard_summary": {
            "covered_sources": 0,
            "configured_sources": 0,
            "source_attempts": 0,
            "source_failures": {"total": 0},
            "time_limited": 0,
        },
        "time_limited": False,
    }

    _reconcile_execution_audit(metadata)

    audit = metadata["pipeline_execution_audit"]
    assert audit["fetched_sources"] == 0
    assert audit["total_sources"] == 0
    assert audit["source_toxicity_rate"] == 0.0
    assert audit["time_limited"] is False


def test_revived_go_health_trips_after_five_incomplete_results() -> None:
    """Five consecutive incomplete revived-Go batches should disable that path."""

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


def test_revived_python_fallback_respects_existing_batch_budget() -> None:
    """Revived fallback should honor the configured Python batch budget."""

    class FakeGoTester:
        available = True

        async def test_custom_configs(
            self,
            configs: list[dict[str, Any]],
            check_honeypot: bool = False,
        ) -> dict[str, bool]:
            """Simulate a Go custom-config tester that returns no results."""

            return {}

        async def test_batch(
            self,
            proxies: list[Proxy],
            check_honeypot: bool = False,
        ) -> list[Proxy]:
            """Simulate a Go batch tester that leaves proxies untouched."""

            return proxies

    class FakePythonTester:
        """Capture revived fallback calls and mark those proxies as working."""

        def __init__(self) -> None:
            self.calls: list[str] = []

        async def test_via_singbox(self, proxy: Proxy) -> Proxy:
            """Pretend the Python fallback verified this revived proxy."""

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

    async def run_batch() -> list[Proxy]:
        """Execute the revived test batch without relying on pytest asyncio plugins."""

        proxies = [_revived_proxy(index) for index in range(5)]
        await tester.test_batch(proxies)
        return proxies

    proxies = asyncio.run(run_batch())

    assert len(python_tester.calls) == 2
    skipped = [
        proxy
        for proxy in proxies
        if proxy.details.get("error") == "REVIVAL_FALLBACK_BUDGET_EXHAUSTED"
    ]
    assert len(skipped) == 3
    assert all(proxy.is_working is False for proxy in skipped)


def test_revived_custom_requests_are_unique_when_proxy_ids_collide() -> None:
    """Chain test results must not collapse at a shared endpoint identity."""

    class FakeGoTester:
        available = True

        def __init__(self) -> None:
            self.request_ids: list[str] = []

        async def test_custom_configs(
            self,
            configs: list[dict[str, Any]],
            check_honeypot: bool = False,
        ) -> dict[str, bool]:
            self.request_ids = [str(config["id"]) for config in configs]
            return {self.request_ids[0]: True, self.request_ids[1]: False}

    tester: Any = object.__new__(SingBoxTester)
    tester.timeout = 1.0
    tester.cache = None
    tester.strict_security = False
    tester.settings = SimpleNamespace(PY_TESTER_BATCH_SIZE=2)
    tester.dry_run = False
    tester.max_workers = 2
    tester.go_tester = FakeGoTester()
    tester._revived_go_failures = 0
    tester._revived_go_failure_limit = 5
    tester._revived_go_disabled = False

    first = _revived_proxy(0)
    second = _revived_proxy(1)
    second.address = first.address
    second.details["chain_outbounds"][0]["tag"] = "other-hop"
    assert first.id == second.id

    results = asyncio.run(tester.test_batch([first, second]))

    assert len(set(tester.go_tester.request_ids)) == 2
    assert [result.is_working for result in results] == [True, False]


def test_shard_sources_defaults_track_repo_root_outside_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shard CLI defaults should resolve from the repo root, not the caller CWD."""

    repo_root = tmp_path / "repo"
    sources_dir = repo_root / "sources"
    sources_dir.mkdir(parents=True)
    (sources_dir / "batch_1.txt").write_text(
        "https://active.example/sub\n", encoding="utf-8"
    )

    outside = tmp_path / "outside"
    outside.mkdir()
    matrix_output = outside / "matrix.json"

    monkeypatch.setattr(shard_sources, "REPO_ROOT", repo_root)
    monkeypatch.chdir(outside)
    monkeypatch.setattr(
        "sys.argv",
        [
            "shard_sources.py",
            "--parts",
            "1",
            "--matrix-output",
            str(matrix_output),
        ],
    )

    assert shard_sources.main() == 0

    payload = json.loads(matrix_output.read_text(encoding="utf-8"))
    assert payload["include"][0]["source_file"] == "sources/runtime/batch_1_part_1.txt"
    assert (repo_root / "sources" / "runtime" / "batch_1_part_1.txt").is_file()
