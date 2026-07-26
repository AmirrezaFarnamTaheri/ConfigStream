# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail closed unless a ConfigStream release is complete and natively validated."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

REQUIRED_NATIVE_TARGETS = {
    "sing-box": "singbox.json",
    "mihomo": "clash.yaml",
    "xray": "xray.json",
}
TRANSIENT_SUFFIXES = (".lock", ".tmp", ".log", ".pyc", ".pyo", ".swp")
BUILTIN_XRAY_TAGS = {"direct", "block"}
BUILTIN_XRAY_PROTOCOLS = {"freedom", "blackhole", "dns"}
NATIVE_REPORT_RELATIVE_PATH = "evidence/native_client_check_report.json"
SINGBOX_ALIAS_PAIRS = (
    ("singbox-chains.json", "chains.json"),
    ("singbox-chains-dns-safe.json", "chains-dns-safe.json"),
    ("singbox-chains-dns-hardened.json", "chains-dns-hardened.json"),
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _safe_path(root: Path, rel: str) -> Path:
    if not rel or "\\" in rel or "\x00" in rel:
        raise ValueError(f"unsafe manifest path: {rel!r}")
    pure = PurePosixPath(rel)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe manifest path: {rel!r}")
    candidate = root.joinpath(*pure.parts)
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve(strict=False)
    if not candidate_resolved.is_relative_to(root_resolved):
        raise ValueError(f"manifest path escapes artifact root: {rel}")
    return candidate


def _artifact_category(rel: str) -> str:
    if rel in {
        "metadata.json",
        "health.json",
        "format_compatibility.json",
        "pipeline_events.jsonl",
    } or rel.startswith("evidence/"):
        return "control"
    if rel.startswith("api/"):
        return "api"
    if rel.startswith("assets/") or rel.endswith(".html"):
        return "frontend"
    if rel.startswith("docs/"):
        return "docs"
    if rel.startswith("data/"):
        return "analytics"
    if rel.endswith(".zip"):
        return "side-product"
    return "artifact"


def _manifest_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        rel = path.relative_to(root).as_posix()
        if path.name.endswith(TRANSIENT_SUFFIXES):
            continue
        if path.is_symlink():
            raise ValueError(f"public artifact must not be a symlink: {rel}")
        entries.append(
            {
                "path": rel,
                "size_bytes": path.stat().st_size,
                "sha256": digest(path),
                "category": _artifact_category(rel),
            }
        )
    return entries


def _validate_manifest(root: Path, manifest: Any) -> list[str]:
    errors: list[str] = []
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list):
        return ["artifact manifest files must be a list"]

    listed: set[str] = set()
    total_size = 0
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            errors.append("malformed artifact manifest entry")
            continue
        rel = item["path"]
        if rel in listed:
            errors.append(f"duplicate manifest path: {rel}")
            continue
        listed.add(rel)
        try:
            path = _safe_path(root, rel)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if path.is_symlink():
            errors.append(f"manifest file is a symlink: {rel}")
            continue
        if not path.is_file():
            errors.append(f"manifest file missing: {rel}")
            continue
        actual_size = path.stat().st_size
        total_size += actual_size
        if item.get("size_bytes") != actual_size:
            errors.append(f"manifest size mismatch: {rel}")
        if digest(path) != item.get("sha256"):
            errors.append(f"manifest hash mismatch: {rel}")

    if isinstance(manifest, dict):
        if manifest.get("file_count") != len(files):
            errors.append("artifact manifest file_count does not match files")
        if manifest.get("total_size_bytes") != total_size:
            errors.append("artifact manifest total_size_bytes does not match files")

    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(
                "public artifact contains symlink: "
                + path.relative_to(root).as_posix()
            )
            continue
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        rel = path.relative_to(root).as_posix()
        if path.name.endswith(TRANSIENT_SUFFIXES):
            errors.append(f"transient file is public: {rel}")
        if rel not in listed:
            errors.append(f"public file omitted from manifest: {rel}")
    return errors


def _validate_native_report(root: Path, report: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["native client report must be an object"]
    if report.get("schema_version") != 2:
        errors.append("native client report schema_version must be 2")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        return errors + ["native client report has no checks"]

    seen: set[tuple[str, str]] = set()
    passed = failed = skipped = 0
    for check in checks:
        if not isinstance(check, dict):
            errors.append("native client report contains malformed check")
            continue
        core = str(check.get("core") or "")
        rel = check.get("path")
        status = check.get("status")
        if not core or not isinstance(rel, str) or not rel:
            errors.append("native client report check is missing core/path")
            continue
        key = (core, rel)
        if key in seen:
            errors.append(f"duplicate native client check: {core}:{rel}")
        seen.add(key)
        if status == "passed":
            passed += 1
        elif status == "failed":
            failed += 1
        elif status == "skipped":
            skipped += 1
        else:
            errors.append(f"unknown native validation status: {core}:{rel}={status}")
        if status != "passed":
            errors.append(f"native validation did not pass: {core}:{rel}={status}")

        try:
            artifact = _safe_path(root, rel)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not artifact.is_file():
            errors.append(f"native validation references missing artifact: {core}:{rel}")
            continue
        expected_digest = check.get("artifact_sha256")
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            errors.append(f"native validation lacks artifact digest: {core}:{rel}")
        elif digest(artifact) != expected_digest:
            errors.append(f"native validation artifact digest mismatch: {core}:{rel}")

    for core, rel in REQUIRED_NATIVE_TARGETS.items():
        if (core, rel) not in seen:
            errors.append(f"missing required native validation: {core}:{rel}")

    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("native client report has no summary")
    else:
        expected = {"passed": passed, "failed": failed, "skipped": skipped}
        for key, value in expected.items():
            if summary.get(key) != value:
                errors.append(f"native client report summary mismatch: {key}")
    return errors


def _validate_xray(root: Path, compatibility: Any) -> list[str]:
    errors: list[str] = []
    xray = load(root / "xray.json")
    outbounds = xray.get("outbounds") if isinstance(xray, dict) else None
    inbounds = xray.get("inbounds") if isinstance(xray, dict) else None
    if not isinstance(inbounds, list) or not inbounds:
        errors.append("xray.json contains no usable inbound listener")
    if not isinstance(outbounds, list):
        return errors + ["xray.json outbounds must be a list"]
    usable = [
        item
        for item in outbounds
        if isinstance(item, dict)
        and item.get("tag") not in BUILTIN_XRAY_TAGS
        and item.get("protocol") not in BUILTIN_XRAY_PROTOCOLS
    ]
    if not usable:
        errors.append("xray.json contains no usable proxy outbound")

    targets = compatibility.get("targets") if isinstance(compatibility, dict) else {}
    target = targets.get("xray") if isinstance(targets, dict) else None
    if isinstance(target, dict):
        emitted = int(target.get("emitted_records") or 0)
        if emitted <= 0:
            errors.append("Xray compatibility report claims no emitted proxy records")
        if emitted > len(usable):
            errors.append("Xray emitted record count exceeds usable outbound count")
    return errors


def _validate_singbox(root: Path) -> list[str]:
    errors: list[str] = []
    paths = sorted({*root.glob("singbox*.json"), *root.glob("chains*.json")})
    for path in paths:
        payload = load(path)
        if not isinstance(payload, dict):
            errors.append(f"{path.name} must be an object")
            continue
        outbounds = payload.get("outbounds")
        endpoints = payload.get("endpoints")
        objects = [
            item
            for collection in (outbounds, endpoints)
            if isinstance(collection, list)
            for item in collection
            if isinstance(item, dict)
        ]
        tags = {str(item.get("tag")) for item in objects if item.get("tag")}
        proxy_tags = {
            str(item.get("tag"))
            for item in objects
            if item.get("tag")
            and item.get("type") not in {"direct", "block", "dns", "selector", "urltest"}
        }
        for item in objects:
            if item.get("type") not in {"selector", "urltest"}:
                continue
            members = item.get("outbounds")
            if not isinstance(members, list) or not members:
                errors.append(f"{path.name} has empty selector/urltest: {item.get('tag')}")
                continue
            valid_members = [member for member in members if member in tags]
            if not valid_members:
                errors.append(
                    f"{path.name} selector/urltest has no resolvable members: "
                    f"{item.get('tag')}"
                )
            if valid_members and all(member == "direct" for member in valid_members):
                errors.append(
                    f"{path.name} selector/urltest fails open to direct: "
                    f"{item.get('tag')}"
                )
        route = payload.get("route")
        final = route.get("final") if isinstance(route, dict) else None
        if proxy_tags and final == "direct":
            errors.append(f"{path.name} route.final bypasses available proxies")

    for canonical, alias in SINGBOX_ALIAS_PAIRS:
        canonical_path = root / canonical
        alias_path = root / alias
        if canonical_path.is_file() and alias_path.is_file():
            if digest(canonical_path) != digest(alias_path):
                errors.append(f"{alias} must be byte-identical to {canonical}")
    return errors


def validate(root: Path, native_report: Path, min_coverage: float) -> list[str]:
    errors: list[str] = []
    required = (
        "proxies.json",
        "metadata.json",
        "health.json",
        "artifact_manifest.json",
        "format_compatibility.json",
        "singbox.json",
        "clash.yaml",
        "xray.json",
    )
    for name in required:
        if not (root / name).is_file():
            errors.append(f"missing required release file: {name}")
    if not native_report.is_file():
        errors.append(f"missing native client report: {native_report}")
    if errors:
        return errors

    metadata = load(root / "metadata.json")
    health = load(root / "health.json")
    manifest = load(root / "artifact_manifest.json")
    records = load(root / "proxies.json")
    compatibility = load(root / "format_compatibility.json")
    report = load(native_report)

    if not isinstance(records, list) or not records:
        errors.append("proxies.json must contain at least one public record")
    if not isinstance(metadata, dict):
        errors.append("metadata.json must be an object")
        metadata = {}
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
        lowered = str(key).lower()
        if any(marker in lowered for marker in ("nonetype", "sequence item", "tester")):
            if int(value or 0):
                errors.append(f"tester infrastructure errors remain: {key}={value}")

    errors.extend(_validate_native_report(root, report))
    native_digest = digest(native_report)
    if isinstance(health, dict) and health.get("native_report_sha256"):
        if health["native_report_sha256"] != native_digest:
            errors.append("health native report digest does not match gate input")

    errors.extend(_validate_xray(root, compatibility))
    errors.extend(_validate_singbox(root))
    errors.extend(_validate_manifest(root, manifest))

    targets = compatibility.get("targets") if isinstance(compatibility, dict) else {}
    for target in REQUIRED_NATIVE_TARGETS:
        target_data = targets.get(target) if isinstance(targets, dict) else None
        if not isinstance(target_data, dict) or target_data.get("status") not in {
            "generated",
            "passed",
        }:
            errors.append(f"compatibility target is not generated: {target}")

    if isinstance(health, dict) and health.get("release_blockers"):
        errors.extend(f"health blocker: {item}" for item in health["release_blockers"])
    return errors


def promote(root: Path, native_report: Path) -> None:
    metadata = load(root / "metadata.json")
    health_path = root / "health.json"
    health = load(health_path)
    manifest_path = root / "artifact_manifest.json"
    manifest = load(manifest_path)
    had_signature = isinstance(manifest, dict) and "manifest_signature" in manifest

    evidence_path = root / NATIVE_REPORT_RELATIVE_PATH
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(native_report, evidence_path)
    native_digest = digest(evidence_path)

    if not isinstance(health, dict):
        raise ValueError("health.json must be an object")
    if not isinstance(metadata, dict):
        raise ValueError("metadata.json must be an object")
    notes = health.get("notes")
    note_list = list(notes) if isinstance(notes, list) else []
    promotion_note = "Promoted only after semantic and native release gates passed."
    if promotion_note not in note_list:
        note_list.append(promotion_note)
    health.update(
        {
            "schema_version": "2.0",
            "status": "ok",
            "total_working": int(
                metadata.get("logical_total_working")
                or metadata.get("total_working")
                or 0
            ),
            "total_tested": int(
                metadata.get("total_tested") or metadata.get("tested") or 0
            ),
            "source_coverage": float(metadata.get("source_coverage") or 0.0),
            "schema_validated": True,
            "native_clients_validated": True,
            "release_blockers": [],
            "native_report": NATIVE_REPORT_RELATIVE_PATH,
            "native_report_sha256": native_digest,
            "notes": note_list,
        }
    )
    health_path.write_text(
        json.dumps(health, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    entries = _manifest_entries(root)
    if not isinstance(manifest, dict):
        manifest = {}
    manifest.pop("manifest_signature", None)
    manifest.update(
        {
            "schema_version": "2.0",
            "generated_at": manifest.get("generated_at")
            or datetime.now(timezone.utc).isoformat(),
            "artifact_generated_at": manifest.get("artifact_generated_at")
            or manifest.get("generated_at")
            or datetime.now(timezone.utc).isoformat(),
            "source_commit": os.environ.get(
                "GITHUB_SHA", str(manifest.get("source_commit") or "")
            ),
            "run_id": os.environ.get(
                "GITHUB_RUN_ID", str(manifest.get("run_id") or "")
            ),
            "run_attempt": os.environ.get(
                "GITHUB_RUN_ATTEMPT", str(manifest.get("run_attempt") or "")
            ),
            "file_count": len(entries),
            "total_size_bytes": sum(int(item["size_bytes"]) for item in entries),
            "files": entries,
        }
    )

    signing_key = os.environ.get("CS_SIGNING_PRIVATE_KEY_HEX")
    if had_signature and not signing_key:
        raise ValueError(
            "promotion would invalidate manifest_signature but no signing key is configured"
        )
    if signing_key:
        from configstream.signer import Signer

        manifest["manifest_signature"] = Signer(signing_key).sign_manifest(manifest)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    post_errors = _validate_manifest(root, manifest)
    if post_errors:
        raise ValueError("post-promotion manifest invalid: " + "; ".join(post_errors))
    if digest(evidence_path) != native_digest:
        raise ValueError("native evidence changed during promotion")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--native-report", type=Path, required=True)
    parser.add_argument("--min-source-coverage", type=float, default=0.80)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    root = args.artifact_dir.resolve()
    native_report = args.native_report.resolve()
    errors = validate(root, native_report, args.min_source_coverage)
    if errors:
        print("ERROR: release gate failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    if args.promote:
        try:
            promote(root, native_report)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"ERROR: release promotion failed: {exc}")
            return 1
    print("OK: release gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
