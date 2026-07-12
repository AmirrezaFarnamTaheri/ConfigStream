# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail-closed public artifact validation and release identity."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping


_PRIVATE_BASENAMES = {
    "test_cache.json",
    "source_quality.db",
    "anomaly.db",
    "history.db",
    "pipeline_events.jsonl",
    "consolidated_pipeline.log",
}
_PRIVATE_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log", ".lock", ".tmp"}
# Deliberately high-confidence patterns. Public frontend code legitimately
# contains field names such as `password` or `apiKey`; those identifiers alone
# are not secrets. These rules target credential-bearing URLs, literal Bearer
# values, private-key blocks, and common long token formats.
_SECRET_PATTERNS = (
    re.compile(
        r"(?i)https?://[^\s\"']+[?&](?:token|api[_-]?key|key|auth|signature|sig)="
        r"(?!example|placeholder|your[-_])[A-Za-z0-9._~+/=-]{8,}"
    ),
    re.compile(r"(?i)authorization\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
)


@dataclass(frozen=True)
class ArtifactViolation:
    code: str
    path: str
    message: str


class ArtifactPolicyError(ValueError):
    def __init__(self, violations: Iterable[ArtifactViolation]):
        self.violations = tuple(violations)
        rendered = "; ".join(
            f"{item.code}({item.path}): {item.message}" for item in self.violations
        )
        super().__init__(rendered or "public artifact rejected")


def _relative_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def _is_private_path(relative: PurePosixPath) -> bool:
    if relative.name in _PRIVATE_BASENAMES:
        return True
    if relative.suffix.lower() in _PRIVATE_SUFFIXES:
        return True
    lowered_parts = {part.lower() for part in relative.parts}
    return bool(lowered_parts & {"private", "private-state", "fingerprints"})


def validate_public_artifact(
    public_root: Path,
    *,
    allowed_paths: Iterable[str],
    required_paths: Iterable[str] = (),
    max_file_bytes: int = 64 * 1024 * 1024,
) -> Mapping[str, str]:
    """Validate exact public file membership, sizes, secrets and produce hashes."""

    root = Path(public_root)
    if not root.is_dir():
        raise ArtifactPolicyError(
            [ArtifactViolation("missing_public_root", str(root), "directory does not exist")]
        )
    if max_file_bytes <= 0:
        raise ValueError("max_file_bytes must be positive")

    allowed = {PurePosixPath(path).as_posix() for path in allowed_paths}
    required = {PurePosixPath(path).as_posix() for path in required_paths}
    actual: set[str] = set()
    digests: dict[str, str] = {}
    violations: list[ArtifactViolation] = []

    for path in _relative_files(root):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        rel = relative.as_posix()
        actual.add(rel)

        if _is_private_path(relative):
            violations.append(
                ArtifactViolation("private_file", rel, "private runtime state is forbidden")
            )
        if rel not in allowed:
            violations.append(
                ArtifactViolation("unexpected_file", rel, "path is not in public allowlist")
            )

        size = path.stat().st_size
        if size > max_file_bytes:
            violations.append(
                ArtifactViolation("file_too_large", rel, f"{size} exceeds {max_file_bytes}")
            )
            continue

        content = path.read_bytes()
        digests[rel] = hashlib.sha256(content).hexdigest()
        if b"\x00" not in content:
            text = content.decode("utf-8", errors="replace")
            for pattern in _SECRET_PATTERNS:
                if pattern.search(text):
                    violations.append(
                        ArtifactViolation(
                            "secret_material",
                            rel,
                            f"matched public secret rule {pattern.pattern!r}",
                        )
                    )
                    break

    for missing in sorted(required - actual):
        violations.append(
            ArtifactViolation("missing_required_file", missing, "required public file absent")
        )

    if violations:
        raise ArtifactPolicyError(violations)
    return dict(sorted(digests.items()))


def write_release_manifest(
    destination: Path,
    *,
    source_commit_sha: str,
    workflow_sha: str,
    image_digest: str,
    policy_digest: str,
    artifact_digests: Mapping[str, str],
    expires_at: datetime,
    parent_release_digest: str | None = None,
) -> dict[str, object]:
    """Write a canonical, content-addressed release manifest."""

    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise ValueError("expires_at must be timezone-aware")
    if expires_at <= now:
        raise ValueError("expires_at must be in the future")

    payload: dict[str, object] = {
        "schema_version": "1",
        "source_commit_sha": source_commit_sha,
        "workflow_sha": workflow_sha,
        "image_digest": image_digest,
        "policy_digest": policy_digest,
        "artifact_digests": dict(sorted(artifact_digests.items())),
        "generated_at": now.isoformat(),
        "expires_at": expires_at.astimezone(timezone.utc).isoformat(),
        "parent_release_digest": parent_release_digest,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["release_id"] = hashlib.sha256(canonical).hexdigest()

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(destination)
    return payload
