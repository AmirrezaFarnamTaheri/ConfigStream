# SPDX-License-Identifier: AGPL-3.0-or-later
"""Runtime readiness evaluation for generated public artifacts.

The module keeps health policy independent from FastAPI so CLI, containers,
and tests all exercise the same readiness contract.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .hashing import sha256_file

_REQUIRED_CONTROL_FILES = (
    "artifact_manifest.json",
    "health.json",
    "metadata.json",
    "proxies.json",
)
_VERIFIED_PAYLOAD_FILES = ("health.json", "metadata.json", "proxies.json")


@dataclass(frozen=True)
class RuntimeHealth:
    status: str
    ready: bool
    checked_at: str
    generated_at: str | None
    age_seconds: float | None
    max_age_seconds: float
    total_working: int
    files_present: int
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        return payload


def _read_object(path: Path) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _manifest_entries(
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], tuple[str, ...]]:
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        return {}, ("manifest_files_invalid",)
    entries: dict[str, Mapping[str, Any]] = {}
    reasons: list[str] = []
    for item in raw_files:
        if not isinstance(item, dict):
            reasons.append("manifest_entry_invalid")
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path:
            reasons.append("manifest_entry_path_invalid")
            continue
        if path in entries:
            reasons.append(f"manifest_duplicate_path:{path}")
            continue
        entries[path] = item
    return entries, tuple(dict.fromkeys(reasons))


def evaluate_runtime_health(
    output_dir: Path,
    *,
    now: datetime | None = None,
    max_age_hours: float = 12.0,
) -> RuntimeHealth:
    """Evaluate whether the public artifact is safe to serve as current output."""

    if max_age_hours <= 0:
        raise ValueError("max_age_hours must be positive")
    checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    root = Path(output_dir)
    reasons: list[str] = []

    if not root.is_dir():
        reasons.append("output_directory_missing")
        files_present = 0
    else:
        files_present = sum(1 for path in root.rglob("*") if path.is_file())
        for filename in _REQUIRED_CONTROL_FILES:
            if not (root / filename).is_file():
                reasons.append(f"required_file_missing:{filename}")

    metadata = _read_object(root / "metadata.json") if root.is_dir() else None
    public_health = _read_object(root / "health.json") if root.is_dir() else None
    manifest = _read_object(root / "artifact_manifest.json") if root.is_dir() else None

    if metadata is None:
        reasons.append("metadata_unreadable")
        metadata = {}
    if public_health is None:
        reasons.append("public_health_unreadable")
        public_health = {}
    if manifest is None:
        reasons.append("manifest_unreadable")
        manifest = {}

    total_working_raw = metadata.get("total_working", public_health.get("total_working", 0))
    try:
        total_working = int(total_working_raw or 0)
    except (TypeError, ValueError):
        total_working = 0
        reasons.append("total_working_invalid")
    if total_working <= 0:
        reasons.append("no_working_proxies")

    public_status = str(public_health.get("status") or "").strip().lower()
    if public_status != "ok":
        reasons.append("public_health_degraded")
    if public_health.get("schema_validated") is not True:
        reasons.append("schema_not_validated")
    blockers = public_health.get("release_blockers")
    if isinstance(blockers, list) and blockers:
        reasons.append("release_blockers_present")

    generated = _parse_timestamp(
        metadata.get("generated_at")
        or metadata.get("last_updated_utc")
        or public_health.get("generated_at")
    )
    age_seconds: float | None = None
    if generated is None:
        reasons.append("generated_at_invalid")
    else:
        age_seconds = (checked_at - generated).total_seconds()
        if age_seconds < -300:
            reasons.append("generated_at_in_future")
        elif age_seconds > max_age_hours * 3600:
            reasons.append(f"artifact_stale:{int(age_seconds)}s")

    entries, manifest_reasons = _manifest_entries(manifest)
    reasons.extend(manifest_reasons)
    if not entries:
        if "manifest_files_invalid" not in reasons:
            reasons.append("manifest_files_invalid")
    else:
        for filename in _VERIFIED_PAYLOAD_FILES:
            entry = entries.get(filename)
            path = root / filename
            if entry is None:
                reasons.append(f"manifest_entry_missing:{filename}")
                continue
            if not path.is_file():
                continue
            expected_size = entry.get("size_bytes")
            expected_digest = entry.get("sha256")
            try:
                actual_size = path.stat().st_size
            except OSError:
                reasons.append(f"manifest_file_unreadable:{filename}")
                continue
            if expected_size != actual_size:
                reasons.append(f"manifest_size_mismatch:{filename}")
            if not isinstance(expected_digest, str) or sha256_file(path) != expected_digest:
                reasons.append(f"manifest_hash_mismatch:{filename}")

    unique_reasons = tuple(dict.fromkeys(reasons))
    ready = not unique_reasons
    return RuntimeHealth(
        status="healthy" if ready else "unhealthy",
        ready=ready,
        checked_at=checked_at.isoformat(),
        generated_at=generated.isoformat() if generated is not None else None,
        age_seconds=age_seconds,
        max_age_seconds=max_age_hours * 3600,
        total_working=total_working,
        files_present=files_present,
        reasons=unique_reasons,
    )
