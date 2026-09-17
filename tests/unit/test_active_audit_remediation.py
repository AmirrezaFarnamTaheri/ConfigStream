# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
import os
from pathlib import Path

import pytest

from configstream.models import Proxy
from configstream.testers.go_tester.binary_security import (
    initialize_binary_identity,
    minimal_subprocess_environment,
)
from configstream.testers.go_tester.process import ProcessManager

ROOT = Path(__file__).resolve().parents[2]


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
    monkeypatch.setenv(
        "CONFIGSTREAM_TESTER_SHA256", hashlib.sha256(original).hexdigest()
    )
    monkeypatch.delenv("CS_STRICT_BINARY_TRUST", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")

    manager = ProcessManager()
    assert manager.binary_path is not None

    tester.write_bytes(b"replaced")
    tester.chmod(0o700)

    with pytest.raises(RuntimeError, match="binary rejected"):
        await manager.ensure_running()


def test_strict_binary_trust_flag_is_case_insensitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tester = tmp_path / "configstream-tester"
    tester.write_bytes(b"trusted")
    tester.chmod(0o700)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CS_STRICT_BINARY_TRUST", "TRUE")
    monkeypatch.delenv("CONFIGSTREAM_TESTER_SHA256", raising=False)

    with pytest.raises(ValueError, match="Strict binary trust requires"):
        initialize_binary_identity(tester)


@pytest.mark.skipif(
    os.name == "nt",
    reason="unsupported platform: test requires POSIX file permission semantics",
)
def test_binary_checksum_sidecar_must_not_be_group_writable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tester = tmp_path / "configstream-tester"
    payload = b"trusted"
    tester.write_bytes(payload)
    tester.chmod(0o700)
    sidecar = tmp_path / "configstream-tester.sha256"
    sidecar.write_text(hashlib.sha256(payload).hexdigest() + "\n", encoding="ascii")
    sidecar.chmod(0o660)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CONFIGSTREAM_TESTER_SHA256", raising=False)

    with pytest.raises(ValueError, match="group/world writable"):
        initialize_binary_identity(tester)


def test_tester_subprocess_environment_does_not_inherit_pipeline_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secrets = {
        "CS_PUBLIC_KEY": "public-key",
        "CS_IPNS_KEY": "ipns-secret",
        "VT_API_KEY": "vt-secret",
        "WARP_KEY_POOL": "warp-secret",
        "CS_SIGNING_PRIVATE_KEY_HEX": "signing-secret",
    }
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)

    environment = minimal_subprocess_environment(object())

    assert set(secrets).isdisjoint(environment)
    assert environment["GOLOG_LOG_LEVEL"] == "error"
    assert environment["PATH"]
    assert environment["TMPDIR"]


def test_preemption_workflow_is_narrow_and_race_safe() -> None:
    workflow = (ROOT / ".github/workflows/preempt-stale-configstream.yml").read_text(
        encoding="utf-8"
    )

    assert 'workflows: ["Config\'s Stream"]' in workflow
    assert "types: [requested]" in workflow
    assert "actions: write" in workflow
    assert "contents: read" in workflow
    assert "pull_request:" not in workflow
    assert "\n  push:\n" not in workflow
    assert "github.event_name == 'push'" not in workflow
    assert "TARGET_SHA" in workflow
    assert "TARGET_RUN_ID" in workflow
    assert "run_id > TARGET_RUN_ID" in workflow
    assert 'elif [[ "$head_sha" == "$TARGET_SHA" ]]' in workflow
    assert "/actions/runs/${run_id}/cancel" in workflow
    assert 'if [[ "$state" != "completed" ]]' in workflow
    assert "Cancel active Retest runs before main execution" in workflow
    assert "if: github.event_name == 'workflow_run'" in workflow
    assert (
        "/actions/workflows/retest.yml/runs?branch=main&status=${status}&per_page=100"
        in workflow
    )
    assert "Failed to cancel still-active Retest run" in workflow
    assert ">/dev/null || true" not in workflow


def test_retest_workflow_never_competes_with_main_pipeline() -> None:
    workflow = (ROOT / ".github/workflows/retest.yml").read_text(encoding="utf-8")

    assert 'cron: "0 2-22/4 * * *"' in workflow
    assert 'cron: "0 */4 * * *"' not in workflow
    assert "for status in queued in_progress" in workflow
    assert (
        "/actions/workflows/main.yml/runs?branch=main&status=${status}&per_page=100"
        in workflow
    )
    assert "Main pipeline has priority over Retest" in workflow
    assert "should_cancel=true" in workflow
    assert "Pipeline has been running for more than 1.5 hours" not in workflow


def test_byow_bridge_bounds_and_serializes_websocket_writes() -> None:
    worker = (ROOT / "tools/worker.js").read_text(encoding="utf-8")

    assert "MAX_WS_MESSAGE_SIZE = 1024 * 1024" in worker
    assert "MAX_WS_BUFFERED_BYTES = 4 * 1024 * 1024" in worker
    assert "MAX_WS_PENDING_MESSAGES = 64" in worker
    assert "chunk.byteLength > MAX_WS_MESSAGE_SIZE" in worker
    assert "pendingMessages >= MAX_WS_PENDING_MESSAGES" in worker
    assert "queuedBytes + chunk.byteLength > MAX_WS_BUFFERED_BYTES" in worker
    assert "shutdown(1009, 'WebSocket message too large')" in worker
    assert "shutdown(1013, 'WebSocket backpressure limit exceeded')" in worker
    assert "pendingMessages += 1" in worker
    assert "queuedBytes += chunk.byteLength" in worker
    assert "pendingMessages = Math.max(0, pendingMessages - 1)" in worker
    assert "queuedBytes = Math.max(0, queuedBytes - chunk.byteLength)" in worker
    assert ".then(() => writeChunk(chunk))" in worker


def test_ipfs_fallback_only_catches_operational_failures() -> None:
    publisher = (ROOT / "scripts/publish_ipfs.py").read_text(encoding="utf-8")

    assert "except (OSError, httpx.HTTPError, RuntimeError):" in publisher
    assert "except (OSError, subprocess.SubprocessError) as e:" in publisher
    assert publisher.count("except Exception") == 1


def test_hugging_face_fallback_only_catches_operational_failures() -> None:
    publisher = (ROOT / "scripts/upload_hf.py").read_text(encoding="utf-8")

    assert "except (OSError, subprocess.SubprocessError):" in publisher
    assert "except (OSError, subprocess.SubprocessError, RuntimeError) as exc:" in publisher
    assert publisher.count("except Exception") == 1
