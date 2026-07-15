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


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


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

    metadata = load(root / "metadata.json")
    health = load(root / "health.json")
    manifest = load(root / "artifact_manifest.json")
    records = load(root / "proxies.json")
    compatibility = load(root / "format_compatibility.json")
    if not isinstance(records, list) or not records:
        errors.append("proxies.json must contain at least one public record")
    coverage = float(metadata.get("source_coverage") or 0.0)
    if coverage < min_coverage:
        errors.append(f"source coverage {coverage:.4f} is below {min_coverage:.4f}")
    if metadata.get("time_limited"):
        errors.append("pipeline was time-limited")
    if int(metadata.get("logical_total_working") or metadata.get("total_working") or 0) <= 0:
        errors.append("no logical working proxies")
    candidates = int(
        metadata.get("shielded_candidate_count")
        or metadata.get("shielded_count")
        or 0
    )
    verified = int(metadata.get("shielded_verified_count") or 0)
    if candidates > verified:
        errors.append(f"{candidates - verified} shielded candidates are unverified")
    for key, value in (metadata.get("drop_reasons") or {}).items():
        if (
            "nonetype" in str(key).lower()
            or "sequence item" in str(key).lower()
        ) and int(value or 0):
            errors.append(f"tester infrastructure errors remain: {key}={value}")

    report = load(native_report)
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
            errors.append(
                "native validation did not pass: "
                f"{core}:{check.get('path')}={check.get('status')}"
            )
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

    targets = compatibility.get("targets") if isinstance(compatibility, dict) else {}
    for target in (
        "sing-box",
        "xray",
        "mihomo",
        "surge",
        "loon",
        "quantumult-x",
    ):
        if (
            not isinstance(targets, dict)
            or not isinstance(targets.get(target), dict)
            or targets[target].get("status") not in {"generated", "passed"}
        ):
            errors.append(f"compatibility target is not generated: {target}")

    if health.get("release_blockers"):
        errors.extend(f"health blocker: {item}" for item in health["release_blockers"])
    return errors


def promote(root: Path, native_report: Path) -> None:
    health_path = root / "health.json"
    health = load(health_path)
    health.update(
        {
            "status": "ok",
            "schema_validated": True,
            "native_clients_validated": True,
            "release_blockers": [],
            "native_report": native_report.name,
        }
    )
    health_path.write_text(
        json.dumps(health, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Promotion mutates health.json, so refresh its manifest entry before publish.
    manifest_path = root / "artifact_manifest.json"
    manifest = load(manifest_path)
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list):
        raise ValueError("artifact manifest files must be a list")
    for item in files:
        if isinstance(item, dict) and item.get("path") == "health.json":
            item["size_bytes"] = health_path.stat().st_size
            item["sha256"] = digest(health_path)
            break
    else:
        files.append(
            {
                "path": "health.json",
                "size_bytes": health_path.stat().st_size,
                "sha256": digest(health_path),
                "category": "control",
            }
        )
    manifest["file_count"] = len(files)
    manifest["total_size_bytes"] = sum(
        int(item.get("size_bytes") or 0) for item in files if isinstance(item, dict)
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--native-report", type=Path, required=True)
    parser.add_argument("--min-source-coverage", type=float, default=0.80)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    errors = validate(args.artifact_dir, args.native_report, args.min_source_coverage)
    if errors:
        print("ERROR: release gate failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    if args.promote:
        promote(args.artifact_dir, args.native_report)
    print("OK: release gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
