# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pinned Slipstream client artifacts and verified async download helpers."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Callable

import httpx

SLIPSTREAM_RELEASE = "42e3e75"
SLIPSTREAM_BASE_URL = (
    "https://github.com/AliRezaBeigy/slipstream-rust-deploy/releases/download/"
    f"{SLIPSTREAM_RELEASE}"
)
MAX_SLIPSTREAM_BYTES = 16 * 1024 * 1024

ProgressCallback = Callable[[int, int, str], None]


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


def verify_artifact(path: Path, expected_sha256: str) -> bool:
    """Return whether ``path`` is bounded and matches the pinned SHA-256 digest."""

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
        return digest.hexdigest() == expected_sha256
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


async def download_verified_artifact(
    *,
    url: str,
    expected_sha256: str,
    destination: Path,
    progress_callback: ProgressCallback | None = None,
    timeout: float = 60.0,
) -> bool:
    """Download one immutable artifact and promote it only after digest verification."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".partial",
        dir=destination.parent,
    )
    os.close(fd)
    partial = Path(temp_name)
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            trust_env=False,
        ) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                declared = _content_length(response)
                if declared is not None and (
                    declared <= 0 or declared > MAX_SLIPSTREAM_BYTES
                ):
                    raise ValueError("Slipstream artifact Content-Length is invalid")

                digest = hashlib.sha256()
                total = 0
                with partial.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > MAX_SLIPSTREAM_BYTES:
                            raise ValueError("Slipstream artifact exceeds size limit")
                        digest.update(chunk)
                        handle.write(chunk)
                        if progress_callback:
                            progress_callback(total, declared or 0, "Downloading")
                    handle.flush()
                    os.fsync(handle.fileno())

                if total <= 0:
                    raise ValueError("Slipstream artifact is empty")
                if digest.hexdigest() != expected_sha256:
                    raise ValueError("Slipstream artifact SHA-256 mismatch")

        os.replace(partial, destination)
        if progress_callback:
            progress_callback(total, declared or total, "Verified")
        return True
    except (OSError, httpx.HTTPError, ValueError):
        partial.unlink(missing_ok=True)
        if progress_callback:
            progress_callback(0, 0, "Verification or download failed")
        return False
