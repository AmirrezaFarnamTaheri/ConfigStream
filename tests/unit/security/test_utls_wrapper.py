# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.security.utls_wrapper import (
    ensure_binary_async,
    test_tls_fingerprint as verify_tls_fingerprint,
)


@pytest.mark.asyncio
async def test_ensure_binary_async_builds_committed_module_without_mutation(tmp_path):
    source = tmp_path / "src" / "go" / "utls_client"
    source.mkdir(parents=True)
    (source / "go.mod").write_text("module utls_client\n", encoding="utf-8")
    (source / "go.sum").write_text("pinned\n", encoding="utf-8")
    binary = tmp_path / "bin" / "utls-client"
    run = AsyncMock(return_value=True)

    with (
        patch("configstream.security.utls_wrapper.BINARY_PATH", binary),
        patch("configstream.security.utls_wrapper.SOURCE_DIR", source),
        patch("configstream.security.utls_wrapper.shutil.which", return_value="/usr/bin/go"),
        patch("configstream.security.utls_wrapper._run_cmd", run),
    ):
        result = await ensure_binary_async()

    assert result is True
    run.assert_awaited_once()
    command = run.await_args.args[0]
    assert command == [
        "go", "build", "-trimpath", "-mod=readonly", "-o", str(binary), "."
    ]
    assert run.await_args.kwargs == {"cwd": source}


@pytest.mark.asyncio
async def test_ensure_binary_async_fail_no_go():
    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("shutil.which", return_value=None),
    ):
        result = await ensure_binary_async()
        assert result is False


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
    process.communicate = AsyncMock(side_effect=__import__('asyncio').TimeoutError)
    process.wait = AsyncMock(return_value=0)

    result = await _communicate_bounded(process, timeout_seconds=0.01)

    assert result is None
    process.kill.assert_called_once_with()
    process.wait.assert_awaited_once_with()
