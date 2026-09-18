# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression coverage for lab chain tester resource and SSRF hardening."""

from __future__ import annotations

import asyncio
import sys
import threading
import types
from typing import Any

import pytest

from configstream.testers import lab_chain_tester


def _nested_outbound(depth: int) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "socks", "server": "1.1.1.1"}
    for _ in range(depth):
        node = {"type": "socks", "server": "1.1.1.1", "detour": node}
    return node


def test_ssrf_validation_fails_closed_on_excessive_nesting() -> None:
    with pytest.raises(ValueError, match="depth"):
        lab_chain_tester._validate_outbound_no_ssrf(_nested_outbound(20))


def test_ssrf_validation_allows_shallow_public_chain() -> None:
    lab_chain_tester._validate_outbound_no_ssrf(_nested_outbound(3))


@pytest.mark.asyncio
async def test_late_singbox_start_is_stopped_after_timeout(monkeypatch) -> None:
    release = threading.Event()
    stopped = threading.Event()

    class SlowSingBox:
        http_proxy_url = "http://127.0.0.1:1"
        socks5_proxy_url = None

        def __init__(self, _path: str) -> None:
            release.wait(5)

        def stop(self) -> None:
            stopped.set()

    fake_module = types.ModuleType("singbox2proxy")
    fake_module.SingBoxProxy = SlowSingBox  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "singbox2proxy", fake_module)
    monkeypatch.setattr(lab_chain_tester, "_SINGBOX_AVAILABLE", True)

    config = {"outbounds": [{"type": "socks", "tag": "p", "server": "1.1.1.1"}]}
    result = await lab_chain_tester.test_chain_config(config, timeout=0.05)
    assert result == {"success": False, "error": "sing-box start timed out"}

    # The start completes after the request gave up; it must not leak.
    release.set()
    for _ in range(100):
        if stopped.is_set():
            break
        await asyncio.sleep(0.02)
    assert stopped.is_set()
