# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from configstream.tools.dns_scanner.python import slipstream_artifacts


class _Stream:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.headers = {"Content-Length": str(len(payload))}

    async def __aenter__(self) -> _Stream:
        return self

    async def __aexit__(self, *_args: object) -> bool:
        return False

    def raise_for_status(self) -> None:
        return None

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        yield self.payload


class _Client:
    payload = b""

    def __init__(self, **_kwargs: object) -> None:
        pass

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_args: object) -> bool:
        return False

    def stream(self, method: str, url: str) -> _Stream:
        assert method == "GET"
        assert "/releases/download/42e3e75/" in url
        return _Stream(self.payload)


def test_manifest_uses_immutable_release_and_arch_specific_linux_assets() -> None:
    artifacts = slipstream_artifacts.SLIPSTREAM_ARTIFACTS

    assert set(artifacts) == {
        "Darwin-x86_64",
        "Darwin-arm64",
        "Linux-x86_64",
        "Linux-arm64",
        "Windows-x86_64",
    }
    assert artifacts["Linux-x86_64"]["filename"].endswith("linux-amd64")
    assert artifacts["Linux-arm64"]["filename"].endswith("linux-arm64")
    assert all("/latest/" not in artifact["url"] for artifact in artifacts.values())
    assert all(
        f"/releases/download/{slipstream_artifacts.SLIPSTREAM_RELEASE}/"
        in artifact["url"]
        for artifact in artifacts.values()
    )


def test_verify_artifact_requires_matching_sha256(tmp_path: Path) -> None:
    path = tmp_path / "slipstream"
    path.write_bytes(b"trusted")
    expected = hashlib.sha256(b"trusted").hexdigest()

    assert slipstream_artifacts.verify_artifact(path, expected)
    assert not slipstream_artifacts.verify_artifact(path, "0" * 64)


@pytest.mark.asyncio
async def test_download_promotes_only_verified_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "slipstream"
    destination.write_bytes(b"old")
    _Client.payload = b"new trusted payload"
    expected = hashlib.sha256(_Client.payload).hexdigest()
    monkeypatch.setattr(slipstream_artifacts.httpx, "AsyncClient", _Client)

    assert await slipstream_artifacts.download_verified_artifact(
        url="https://example.invalid/releases/download/42e3e75/slipstream",
        expected_sha256=expected,
        destination=destination,
    )
    assert destination.read_bytes() == _Client.payload
    assert not destination.with_name(f".{destination.name}.partial").exists()

    destination.write_bytes(b"known-good")
    assert not await slipstream_artifacts.download_verified_artifact(
        url="https://example.invalid/releases/download/42e3e75/slipstream",
        expected_sha256="f" * 64,
        destination=destination,
    )
    assert destination.read_bytes() == b"known-good"
    assert not destination.with_name(f".{destination.name}.partial").exists()
