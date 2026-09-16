# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
from pathlib import Path

import pytest

from configstream.models import Proxy
from configstream.testers.go_tester.process import ProcessManager


@pytest.mark.parametrize("process", ["revived-warp", "revived-vwarp"])
def test_revived_proxy_cannot_start_working_without_test_evidence(process: str) -> None:
    proxy = Proxy(
        config="socks5://127.0.0.1:10808",
        protocol="socks5",
        address="127.0.0.1",
        port=10808,
        process=process,
        is_working=True,
    )

    assert proxy.tested_at == ""
    assert proxy.is_working is False


def test_timestamped_revived_proxy_can_preserve_verified_health() -> None:
    proxy = Proxy(
        config="socks5://127.0.0.1:10808",
        protocol="socks5",
        address="127.0.0.1",
        port=10808,
        process="revived-vwarp",
        is_working=True,
        tested_at="2026-09-16T12:00:00+00:00",
    )

    assert proxy.is_working is True


@pytest.mark.asyncio
async def test_standalone_process_manager_rejects_pinned_binary_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tester = tmp_path / "configstream-tester"
    original = b"first"
    tester.write_bytes(original)
    tester.chmod(0o700)
    monkeypatch.setenv("CONFIGSTREAM_TESTER_BIN", str(tester))
    monkeypatch.setenv("CONFIGSTREAM_TESTER_SHA256", hashlib.sha256(original).hexdigest())
    monkeypatch.delenv("CS_STRICT_BINARY_TRUST", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    manager = ProcessManager()
    assert manager.binary_path is not None

    tester.write_bytes(b"replaced")
    tester.chmod(0o700)

    with pytest.raises(RuntimeError, match="binary rejected"):
        await manager.ensure_running()


def test_preemption_workflow_is_narrow_and_privileged_only_for_actions() -> None:
    workflow = Path(".github/workflows/preempt-stale-configstream.yml").read_text(
        encoding="utf-8"
    )

    assert 'workflows: ["Config\'s Stream"]' in workflow
    assert "types: [requested]" in workflow
    assert "actions: write" in workflow
    assert "contents: read" in workflow
    assert "pull_request:" not in workflow
    assert "head_sha" in workflow
    assert "TARGET_SHA" in workflow
    assert "/actions/runs/${run_id}/cancel" in workflow
