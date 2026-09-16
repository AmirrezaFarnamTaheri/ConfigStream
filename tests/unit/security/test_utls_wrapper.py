# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.security.utls_wrapper import (
    _minimal_subprocess_environment,
    _verify_binary_checksum,
    ensure_binary_async,
    test_tls_fingerprint as verify_tls_fingerprint,
)


@pytest.mark.asyncio
async def test_ensure_binary_async_builds_committed_module_with_digest_sidecar(
    tmp_path: Path,
):
    source = tmp_path / "src" / "go" / "utls_client"
    source.mkdir(parents=True)
    (source / "go.mod").write_text("module utls_client\n", encoding="utf-8")
    (source / "go.sum").write_text("pinned\n", encoding="utf-8")
    binary = tmp_path / "bin" / "utls-client"
    commands: list[tuple[list[str], Path]] = []

    async def run(cmd: list[str], cwd: Path, **_kwargs) -> bool:
        commands.append((cmd, cwd))
        output = Path(cmd[cmd.index("-o") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"locally-built-utls")
        return True

    with (
        patch("configstream.security.utls_wrapper.BINARY_PATH", binary),
        patch("configstream.security.utls_wrapper.SOURCE_DIR", source),
        patch(
            "configstream.security.utls_wrapper.shutil.which",
            return_value="/usr/bin/go",
        ),
        patch("configstream.security.utls_wrapper._run_cmd", side_effect=run),
    ):
        result = await ensure_binary_async()

    assert result is True
    assert len(commands) == 1
    command, cwd = commands[0]
    assert cwd == source
    assert command[:5] == [
        "/usr/bin/go",
        "build",
        "-trimpath",
        "-mod=readonly",
        "-o",
    ]
    assert command[-1] == "."
    assert binary.read_bytes() == b"locally-built-utls"
    sidecar = binary.with_name(binary.name + ".sha256")
    assert (
        sidecar.read_text(encoding="ascii").strip()
        == hashlib.sha256(binary.read_bytes()).hexdigest()
    )


@pytest.mark.asyncio
async def test_ensure_binary_async_fail_no_go():
    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("shutil.which", return_value=None),
    ):
        result = await ensure_binary_async()
        assert result is False


def test_utls_existing_binary_requires_trusted_digest(tmp_path: Path, monkeypatch):
    binary = tmp_path / "utls-client"
    binary.write_bytes(b"existing")
    binary.chmod(0o700)
    monkeypatch.delenv("UTLS_CLIENT_SHA256", raising=False)

    assert _verify_binary_checksum(binary) is False


def test_utls_minimal_environment_excludes_pipeline_secrets(monkeypatch):
    secrets = (
        "CS_PUBLIC_KEY",
        "CS_IPNS_KEY",
        "VT_API_KEY",
        "WARP_KEY_POOL",
        "CS_SIGNING_PRIVATE_KEY_HEX",
    )
    for name in secrets:
        monkeypatch.setenv(name, "sensitive")

    # These values must not be able to weaken the build isolation contract.
    monkeypatch.setenv("GOENV", "/tmp/attacker-goenv")
    monkeypatch.setenv("GOTOOLCHAIN", "auto")
    monkeypatch.setenv("GOWORK", "/tmp/attacker.work")
    monkeypatch.setenv("CGO_ENABLED", "1")
    monkeypatch.setenv("GOFLAGS", "-toolexec=/tmp/attacker")

    probe_env = _minimal_subprocess_environment()
    build_env = _minimal_subprocess_environment(include_go=True)

    assert probe_env["PATH"]
    assert probe_env["TMPDIR"]
    assert all(name not in probe_env for name in secrets)
    assert all(name not in build_env for name in secrets)
    assert "GOFLAGS" not in build_env
    assert build_env["GOENV"] == "off"
    assert build_env["GOTOOLCHAIN"] == "local"
    assert build_env["GOWORK"] == "off"
    assert build_env["CGO_ENABLED"] == "0"


@pytest.mark.asyncio
async def test_verify_tls_fingerprint_success():
    with (
        patch(
            "configstream.security.utls_wrapper.ensure_binary_async",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "configstream.security.utls_wrapper._verify_binary_checksum",
            return_value=True,
        ),
        patch("asyncio.create_subprocess_exec") as mock_exec,
    ):
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"Success", b""))
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        result = await verify_tls_fingerprint("https://example.com", "1.2.3.4:443")
        assert result is True
        assert mock_exec.call_args.kwargs["env"] == _minimal_subprocess_environment()


@pytest.mark.asyncio
async def test_verify_tls_fingerprint_fail():
    with (
        patch(
            "configstream.security.utls_wrapper.ensure_binary_async",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "configstream.security.utls_wrapper._verify_binary_checksum",
            return_value=True,
        ),
        patch("asyncio.create_subprocess_exec") as mock_exec,
    ):
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc

        result = await verify_tls_fingerprint("https://example.com", "1.2.3.4:443")
        assert result is False


@pytest.mark.asyncio
async def test_bounded_communicate_kills_timed_out_child():
    from configstream.security.utls_wrapper import _communicate_bounded

    process = MagicMock()
    process.returncode = None
    process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
    process.wait = AsyncMock(return_value=-9)

    result = await _communicate_bounded(process, timeout_seconds=0.01)

    assert result is None
    process.kill.assert_called_once_with()
    process.wait.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_bounded_communicate_reaps_on_caller_cancellation():
    from configstream.security.utls_wrapper import _communicate_bounded

    process = MagicMock()
    process.returncode = None
    process.communicate = AsyncMock(side_effect=asyncio.CancelledError)
    process.wait = AsyncMock(return_value=-9)

    with pytest.raises(asyncio.CancelledError):
        await _communicate_bounded(process, timeout_seconds=30)

    process.kill.assert_called_once_with()
    process.wait.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_bounded_communicate_reaps_without_killing_already_exited_child():
    from configstream.security.utls_wrapper import _communicate_bounded

    process = MagicMock()
    process.returncode = 0
    process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
    process.wait = AsyncMock(return_value=0)

    assert await _communicate_bounded(process, timeout_seconds=0.01) is None

    process.kill.assert_not_called()
    process.wait.assert_awaited_once_with()
