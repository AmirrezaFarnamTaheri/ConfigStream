# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from configstream.security import blocklist as blocklist_module
from configstream.security.blocklist import BlocklistManager


@pytest.fixture(autouse=True)
def _reset_blocklist_singleton() -> Iterator[None]:
    BlocklistManager._instance = None
    yield
    BlocklistManager._instance = None


def _patch_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cache = tmp_path / "blocklist.txt"
    monkeypatch.setattr(blocklist_module, "CACHE_FILE", cache)
    monkeypatch.setattr(blocklist_module, "METADATA_FILE", tmp_path / "metadata.json")
    monkeypatch.setattr(blocklist_module, "MIN_BLOCKLIST_NETWORKS", 1)
    return cache


class _Response:
    status_code = 200
    headers: dict[str, str] = {}

    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class _Client:
    payload = b""

    def __init__(self, **_kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, _url: str, **_kwargs):
        return _Response(self.payload)


@pytest.mark.asyncio
async def test_malformed_candidate_preserves_last_known_good(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _patch_paths(tmp_path, monkeypatch)
    cache.write_text("1.1.1.0/24\n2.2.2.0/24\n", encoding="utf-8")
    _Client.payload = b"<html>upstream error</html>"
    monkeypatch.setattr(blocklist_module.httpx, "AsyncClient", _Client)

    manager = BlocklistManager()
    await manager.update()

    assert cache.read_text(encoding="utf-8") == "1.1.1.0/24\n2.2.2.0/24\n"
    assert manager.is_blocked("1.1.1.10")
    assert manager.is_blocked("2.2.2.20")


@pytest.mark.asyncio
async def test_dangerous_shrink_preserves_last_known_good(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _patch_paths(tmp_path, monkeypatch)
    cache.write_text(
        "".join(f"10.0.{index}.0/24\n" for index in range(10)), encoding="utf-8"
    )
    _Client.payload = b"203.0.113.0/24\n"
    monkeypatch.setattr(blocklist_module.httpx, "AsyncClient", _Client)

    manager = BlocklistManager()
    await manager.update()

    assert "10.0.9.0/24" in cache.read_text(encoding="utf-8")
    assert manager.is_blocked("10.0.9.1")
    assert not manager.is_blocked("203.0.113.1")


@pytest.mark.asyncio
async def test_broad_prefixes_are_not_lost_by_bucket_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _patch_paths(tmp_path, monkeypatch)
    cache.write_text("10.0.0.0/7\n2001::/15\n", encoding="utf-8")

    manager = BlocklistManager()
    await manager.load()

    assert manager.is_blocked("11.255.255.255")
    assert manager.is_blocked("2001:ffff::1")
