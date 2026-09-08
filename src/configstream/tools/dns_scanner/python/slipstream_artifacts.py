# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pinned Slipstream client artifacts and verified download helpers."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

import httpx

SLIPSTREAM_RELEASE = "42e3e75"
SLIPSTREAM_BASE_URL = (
    "https://github.com/AliRezaBeigy/slipstream-rust-deploy/releases/download/"
    f"{SLIPSTREAM_RELEASE}"
)
MAX_SLIPSTREAM_BYTES = 16 * 1024 * 1024


def _artifact(filename: str, sha256: str) -> dict[str, str]:
    return {
        "filename": filename,
        "sha256": sha256,
        "url": f"{SLIPSTREAM_BASE_URL}/{filename}",
    }


SLIPSTREAM_ARTIFACTS: dict[str, dict[str, str]] = {
    "Darwin-x86_64": _artifact(
        "slipstream-client-darwin-amd64",
        "85c10b0da9b0e160c72630ccb28e7938854baf6033b235a3fdbaff1a4ecceed1",
    ),
    "Darwin-arm64": _artifact(
        "slipstream-client-darwin-arm64",
        "b12657e204e88c52e59b4a76719699a1817739631393fd5d48aff030a0fcabac",
    ),
    "Linux-x86_64": _artifact(
        "slipstream-client-linux-amd64",
        "677eb993a8033f1bbec1739b36c7d233b23da98f35b00e1d9181f7c0b994e0b1",
    ),
    "Linux-arm64": _artifact(
        "slipstream-client-linux-arm64",
        "ba8c0354d003fd61d797554c810bf6347e989b1d36fdcc4dfdaddd05a12b358a",
    ),
    "Windows-x86_64": _artifact(
        "slipstream-client-windows-amd64.exe",
        "63988d9566ad3d7ceead07a5b75bbc9e62ed71a15056afeca9650e432330dbea",
    ),
}


def verify_artifact(path: Path, artifact: Mapping[str, str]) -> bool:
    """Return whether ``path`` matches the pinned size and digest contract."""

    try:
        if not path.is_file():
            return False
        size = path.stat().st_size
        if size <= 0 or size > MAX_SLIPSTREAM_BYTES:
            return False
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest() == artifact["sha256"]
    except OSError:
        return False


def _content_length(response: httpx.Response) -> int | None:
    value = response.headers.get("Content-Length")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def download_verified_artifact(
    artifact: Mapping[str, str],
    destination: Path,
    *,
    retries: int = 3,
    timeout: float = 60.0,
    client_factory: Any = httpx.Client,
) -> bool:
    """Download one immutable Slipstream artifact and promote it after SHA-256 verification."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f".{destination.name}.partial")
    for _attempt in range(max(1, retries)):
        try:
            partial.unlink(missing_ok=True)
            with client_factory(
                timeout=httpx.Timeout(timeout),
                follow_redirects=True,
            ) as client:
                with client.stream("GET", artifact["url"]) as response:
                    response.raise_for_status()
                    declared = _content_length(response)
                    if declared is not None and (
                        declared <= 0 or declared > MAX_SLIPSTREAM_BYTES
                    ):
                        raise ValueError("Slipstream artifact Content-Length is invalid")
                    digest = hashlib.sha256()
                    total = 0
                    with partial.open("wb") as handle:
                        for chunk in response.iter_bytes():
                            if not chunk:
                                continue
                            total += len(chunk)
                            if total > MAX_SLIPSTREAM_BYTES:
                                raise ValueError("Slipstream artifact exceeds size limit")
                            digest.update(chunk)
                            handle.write(chunk)
                        handle.flush()
                        os.fsync(handle.fileno())
                    if total <= 0:
                        raise ValueError("Slipstream artifact is empty")
                    if digest.hexdigest() != artifact["sha256"]:
                        raise ValueError("Slipstream artifact SHA-256 mismatch")
            os.replace(partial, destination)
            return True
        except (OSError, httpx.HTTPError, ValueError):
            partial.unlink(missing_ok=True)
    return False
