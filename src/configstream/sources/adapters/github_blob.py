# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bounded acquisition of an exact GitHub repository blob."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import AsyncIterator

import httpx

from ..models import SourceProvider, SourceSnapshotManifest
from ..policy import validate_snapshot
from ..registry import assert_repository_allowed

_SHA1 = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class AcquiredSnapshot:
    content: bytes
    manifest: SourceSnapshotManifest


class GitHubBlobAdapter:
    """Fetch an exact commit/path with finite bytes and immutable identity.

    The caller must resolve and provide both the commit SHA and Git blob SHA
    through a trusted GitHub API response. Floating branches are deliberately
    unsupported by this adapter.
    """

    def __init__(self, provider: SourceProvider):
        self.provider = provider

    @staticmethod
    def _validate_path(path: str) -> str:
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise ValueError("source path must be a relative repository path")
        return candidate.as_posix()

    @staticmethod
    async def _bounded_chunks(
        response: httpx.Response,
        *,
        max_bytes: int,
    ) -> AsyncIterator[bytes]:
        consumed = 0
        async for chunk in response.aiter_bytes():
            consumed += len(chunk)
            if consumed > max_bytes:
                raise ValueError(
                    f"source response exceeded maximum size {max_bytes} bytes"
                )
            yield chunk

    async def acquire(
        self,
        client: httpx.AsyncClient,
        *,
        commit_sha: str,
        blob_sha: str,
        path: str,
        upstream_commit_time: datetime,
        run_id: str,
        protocol_claim: str | None = None,
        fetched_at: datetime | None = None,
    ) -> AcquiredSnapshot:
        if not _SHA1.fullmatch(commit_sha):
            raise ValueError("commit_sha must be a full lowercase Git SHA-1")
        if not _SHA1.fullmatch(blob_sha):
            raise ValueError("blob_sha must be a full lowercase Git SHA-1")
        normalized_path = self._validate_path(path)
        repository = self.provider.canonical_repository_full_name
        assert_repository_allowed(repository)

        fetched = (fetched_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if upstream_commit_time.tzinfo is None or upstream_commit_time.utcoffset() is None:
            raise ValueError("upstream_commit_time must be timezone-aware")
        upstream_commit_time = upstream_commit_time.astimezone(timezone.utc)

        url = (
            "https://raw.githubusercontent.com/"
            f"{self.provider.canonical_owner}/"
            f"{self.provider.canonical_repository}/"
            f"{commit_sha}/{normalized_path}"
        )
        async with client.stream(
            "GET",
            url,
            follow_redirects=False,
            headers={"Accept": "text/plain, application/octet-stream"},
        ) as response:
            if 300 <= response.status_code < 400:
                raise ValueError("source acquisition refused an HTTP redirect")
            response.raise_for_status()
            content = b"".join(
                [
                    chunk
                    async for chunk in self._bounded_chunks(
                        response,
                        max_bytes=self.provider.max_response_bytes,
                    )
                ]
            )

        # Empty lines do not represent records; malformed records remain the
        # parser's responsibility after the snapshot itself passes policy.
        record_count = sum(1 for line in content.splitlines() if line.strip())
        manifest = SourceSnapshotManifest(
            run_id=run_id,
            provider_id=self.provider.provider_id,
            requested_locator=url,
            resolved_canonical_locator=url,
            repository_owner=self.provider.canonical_owner,
            repository_name=self.provider.canonical_repository,
            ref=commit_sha,
            commit_sha=commit_sha,
            blob_sha=blob_sha,
            content_sha256=hashlib.sha256(content).hexdigest(),
            byte_length=len(content),
            record_count=record_count,
            fetched_at=fetched,
            upstream_commit_time=upstream_commit_time,
            expires_at=fetched
            + timedelta(seconds=self.provider.max_snapshot_age_seconds),
            license_spdx=self.provider.license_spdx,
            protocol_claim=protocol_claim,
        )
        validate_snapshot(self.provider, manifest, now=fetched)
        return AcquiredSnapshot(content=content, manifest=manifest)
