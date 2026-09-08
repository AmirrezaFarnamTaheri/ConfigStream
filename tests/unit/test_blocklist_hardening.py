# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import ipaddress
from pathlib import Path

import pytest

from configstream.security import blocklist as blocklist_module
from configstream.security.blocklist import IPBlocklist


@pytest.mark.asyncio
async def test_malformed_candidate_preserves_last_known_good(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "blocklist.txt"
    cache.write_text("1.1.1.0/24\n2.2.2.0/24\n", encoding="utf-8")
    monkeypatch.setattr(blocklist_module, "CACHE_FILE", cache)
    monkeypatch.setattr(blocklist_module, "MIN_BLOCKLIST_NETWORKS", 1)
    blocklist = IPBlocklist()

    class _Response:
        content = b"<html>upstream error</html>"

        def raise_for_status(self) -> None:
            return None

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url: str):
            return _Response()

    monkeypatch.setattr(blocklist_module.httpx, "AsyncClient", lambda **_kwargs: _Client())

    assert not await blocklist.update()
    assert cache.read_text(encoding="utf-8") == "1.1.1.0/24\n2.2.2.0/24\n"


@pytest.mark.asyncio
async def test_dangerous_shrink_preserves_last_known_good(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "blocklist.txt"
    cache.write_text(
        "".join(f"10.0.{index}.0/24\n" for index in range(10)), encoding="utf-8"
    )
    monkeypatch.setattr(blocklist_module, "CACHE_FILE", cache)
    monkeypatch.setattr(blocklist_module, "MIN_BLOCKLIST_NETWORKS", 1)
    blocklist = IPBlocklist()

    class _Response:
        content = b"203.0.113.0/24\n"

        def raise_for_status(self) -> None:
            return None

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url: str):
            return _Response()

    monkeypatch.setattr(blocklist_module.httpx, "AsyncClient", lambda **_kwargs: _Client())

    assert not await blocklist.update()
    assert "10.0.9.0/24" in cache.read_text(encoding="utf-8")


def test_broad_prefixes_are_not_lost_by_bucket_index() -> None:
    blocklist = IPBlocklist()
    blocklist.blocked_networks = [
        ipaddress.ip_network("10.0.0.0/7"),
        ipaddress.ip_network("2001:db8::/15"),
    ]
    blocklist._rebuild_index()

    assert blocklist.is_blocked("11.255.255.255")
    assert blocklist.is_blocked("2000:ffff::1")
