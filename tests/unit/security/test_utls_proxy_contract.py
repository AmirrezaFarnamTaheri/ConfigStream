# SPDX-License-Identifier: AGPL-3.0-or-later
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configstream.security.utls_wrapper import test_tls_fingerprint


@pytest.mark.asyncio
async def test_tls_fingerprint_forwards_proxy_as_explicit_argv() -> None:
    process = MagicMock()
    process.communicate = AsyncMock(return_value=(b"Success", b""))
    process.returncode = 0

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
        patch(
            "configstream.security.utls_wrapper.asyncio.create_subprocess_exec",
            return_value=process,
        ) as execute,
    ):
        assert await test_tls_fingerprint(
            "https://example.com/probe",
            "http://127.0.0.1:8080",
            "firefox",
        )

    argv = execute.call_args.args
    assert argv[0].endswith("utls-client")
    assert argv[1:5] == ("-url", "https://example.com/probe", "-fp", "firefox")
    assert argv[5:7] == ("-proxy", "http://127.0.0.1:8080")
    assert execute.call_args.kwargs["shell"] if "shell" in execute.call_args.kwargs else True
