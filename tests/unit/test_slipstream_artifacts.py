# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

from configstream.tools.dns_scanner.python import slipstream_artifacts


class _Stream:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self):
        yield self.payload


class _Client:
    payload = b""

    def __init__(self, **_kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
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
        f"/releases/download/{slipstream_artifacts.SLIPSTREAM_RELEASE}/" in artifact["url"]
        for artifact in artifacts.values()
    )


def test_verify_artifact_requires_matching_sha256(tmp_path: Path) -> None:
    path = tmp_path / "slipstream"
    path.write_bytes(b"trusted")
    artifact = {
        "url": "https://example.invalid/slipstream",
        "filename": "slipstream",
        "sha256": hashlib.sha256(b"trusted").hexdigest(),
    }

    assert slipstream_artifacts.verify_artifact(path, artifact)
    artifact["sha256"] = "0" * 64
    assert not slipstream_artifacts.verify_artifact(path, artifact)


def test_download_promotes_only_verified_payload(tmp_path: Path) -> None:
    destination = tmp_path / "slipstream"
    destination.write_bytes(b"old")
    _Client.payload = b"new trusted payload"
    artifact = {
        "url": "https://example.invalid/releases/download/42e3e75/slipstream",
        "filename": "slipstream",
        "sha256": hashlib.sha256(_Client.payload).hexdigest(),
    }

    assert slipstream_artifacts.download_verified_artifact(
        artifact,
        destination,
        client_factory=_Client,
    )
    assert destination.read_bytes() == _Client.payload
    assert not destination.with_name(f".{destination.name}.partial").exists()

    destination.write_bytes(b"known-good")
    bad_artifact = dict(artifact)
    bad_artifact["sha256"] = "f" * 64
    assert not slipstream_artifacts.download_verified_artifact(
        bad_artifact,
        destination,
        retries=1,
        client_factory=_Client,
    )
    assert destination.read_bytes() == b"known-good"
    assert not destination.with_name(f".{destination.name}.partial").exists()
