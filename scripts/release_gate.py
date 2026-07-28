# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail closed unless a ConfigStream release is complete and natively validated."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_NATIVE_CORES = {"sing-box", "mihomo", "xray"}
TRANSIENT_SUFFIXES = (".lock", ".tmp", ".log", ".pyc", ".pyo", ".swp")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_checked(path: Path, errors: list[str]) -> Any:
    try:
        return load(path)
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"{path.name} is not readable JSON: {type(exc).__name__}")
        return None


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def safe_int(value: Any) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def safe_float(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def validate(root: Path, native_report: Path, min_coverage: float) -> list[str]:
    errors: list[str] = []
    for name in (
        "proxies.json",
        "metadata.json",
        "health.json",
        "artifact_manifest.json",
        "format_compatibility.json",
        "singbox.json",
        "clash.yaml",
        "xray.json",
    ):
        if not (root / name).is_file():
            errors.append(f"missing required release file: {name}")
    if errors:
        return errors

    metadata = load_checked(root / "metadata.json", errors)
    health = load_checked(root / "health.json", errors)
    manifest = load_checked(root / "artifact_manifest.json", errors)
    records = load_checked(root / "proxies.json", errors)
    compatibility = load_checked(root / "format_compatibility.json", errors)
    if errors:
        return errors

    if not isinstance(records, list) or not records:
        errors.append("proxies.json must contain at least one public record")
    if not isinstance(metadata, dict):
        errors.append("metadata.json must be an object")
        metadata = {}
    coverage = safe_float(metadata.get("source_coverage"))
    if coverage < min_coverage:
        errors.append(f"source coverage {coverage:.4f} is below {min_coverage:.4f}")
    if metadata.get("time_limited"):
        errors.append("pipeline was time-limited")
    if safe_int(metadata.get("logical_total_working") or metadata.get("total_working")) <= 0:
        errors.append("no logical working proxies")
    candidates = safe_int(metadata.get("shielded_candidate_count") or metadata.get("shielded_count"))
    verified = safe_int(metadata.get("shielded_verified_count"))
    if candidates > verified:
        errors.append(f"{candidates - verified} shielded candidates are unverified")
    drop_reasons = metadata.get("drop_reasons")
    if isinstance(drop_reasons, dict):
        for key, value in drop_reasons.items():
            if ("nonetype" in str(key).lower() or "sequence item" in str(key).lower()) and safe_int(value):
                errors.append(f"tester infrastructure errors remain: {key}={value}")

    report = load_checked(native_report, errors)
    checks = report.get("checks") if isinstance(report, dict) else None
    if not isinstance(checks, list):
        errors.append("native client report has no checks")
        checks = []

    cores_seen: set[str] = set()
    for check in checks:
        if not isinstance(check, dict):
            continue
        core = str(check.get("core") or "")
        cores_seen.add(core)
        if check.get("status") != "passed":
            errors.append(f"native validation did not pass: {core}:{check.get('path')}={check.get('status')}")

    missing = REQUIRED_NATIVE_CORES - cores_seen
    if missing:
        errors.append("missing native validators: " + ", ".join(sorted(missing)))

    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list):
        errors.append("artifact manifest files must be a list")
        files = []

    listed = set()
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            errors.append("malformed artifact manifest entry")
            continue
        rel = item["path"]
        listed.add(rel)
        path = root / rel
        if not path.is_file():
            errors.append(f"manifest file missing: {rel}")
        elif digest(path) != item.get("sha256"):
            errors.append(f"manifest hash mismatch: {rel}")

    for path in root.rglob("*"):
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        rel = path.relative_to(root).as_posix()
        if path.name.endswith(TRANSIENT_SUFFIXES):
            errors.append(f"transient file is public: {rel}")
        if rel not in listed:
            errors.append(f"public file omitted from manifest: {rel}")

    return errors
