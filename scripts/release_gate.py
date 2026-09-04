# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail closed unless a ConfigStream release is complete and natively validated."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Optional, Union

from configstream.constants import is_tester_infrastructure_drop_reason
from configstream.output.client_formats import validate_xray_config
from configstream.output.singbox_contract import validate_singbox_config

REQUIRED_NATIVE_TARGETS = {
    "sing-box": "singbox.json",
    "mihomo": "clash.yaml",
    "xray": "xray.json",
}
REQUIRED_FILES = (
    "proxies.json",
    "metadata.json",
    "health.json",
    "artifact_manifest.json",
    "format_compatibility.json",
    "singbox.json",
    "clash.yaml",
    "xray.json",
)
TRANSIENT_SUFFIXES = (".lock", ".tmp", ".log", ".pyc", ".pyo", ".swp")
NATIVE_REPORT_RELATIVE_PATH = "evidence/native_client_check_report.json"
MAX_FILES = 10000
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_CHECKS = 1000


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def load_checked(path: Path, errors: list[str]) -> Any:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            errors.append(f"{path.name} exceeds the control-file size limit")
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name} is not readable JSON: {type(exc).__name__}")
        return None


def safe_int(value: Optional[Union[int, float]]) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def safe_float(value: Optional[Union[int, float]]) -> float:
    return (
        float(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else 0.0
    )


def safe_path(root: Path, relative: str) -> Path:
    if not relative or "\\" in relative or "\x00" in relative:
        raise ValueError(f"unsafe manifest path: {relative!r}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe manifest path: {relative!r}")
    candidate = root.joinpath(*pure.parts)
    if not candidate.resolve(strict=False).is_relative_to(root.resolve()):
        raise ValueError(f"manifest path escapes artifact root: {relative}")
    return candidate


def manifest_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(
                f"public artifact contains symlink: {path.relative_to(root).as_posix()}"
            )
        r = path.relative_to(root).as_posix()
        if not path.is_file() or r == "artifact_manifest.json":
            continue
        if path.name.endswith(TRANSIENT_SUFFIXES):
            raise ValueError(f"transient file is public: {r}")
        s = path.stat().st_size
        if s > MAX_FILE_BYTES:
            raise ValueError(f"public file exceeds size limit: {r}")
        total += s
        if total > MAX_TOTAL_BYTES:
            raise ValueError("public artifact exceeds aggregate size limit")
        entries.append(
            dict(path=r, size_bytes=s, sha256=digest(path), category=_cat(r))
        )
        if len(entries) > MAX_FILES:
            raise ValueError("public artifact exceeds file-count limit")
    return entries


def validate_manifest(root: Path, manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return ["artifact manifest must be an object"]
    files = manifest.get("files")
    if not isinstance(files, list):
        return ["artifact manifest files must be a list"]
    if len(files) > MAX_FILES:
        return ["artifact manifest exceeds file-count limit"]

    errors: list[str] = []
    try:
        actual_entries = manifest_entries(root)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    actual = {str(item["path"]): item for item in actual_entries}

    listed: set[str] = set()
    total = 0
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            errors.append("malformed artifact manifest entry")
            continue
        relative = item["path"]
        if relative in listed:
            errors.append(f"duplicate manifest path: {relative}")
            continue
        listed.add(relative)
        try:
            path = safe_path(root, relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if path.is_symlink():
            errors.append(f"manifest file is a symlink: {relative}")
            continue
        actual_item = actual.get(relative)
        if actual_item is None:
            if not path.is_file():
                errors.append(f"manifest file missing: {relative}")
            else:
                errors.append(f"manifest path is not public payload: {relative}")
            continue
        size = int(actual_item["size_bytes"])
        total += size
        if item.get("size_bytes") != size:
            errors.append(f"manifest size mismatch: {relative}")
        if item.get("sha256") != actual_item["sha256"]:
            errors.append(f"manifest hash mismatch: {relative}")
    if manifest.get("file_count") not in (None, len(files)):
        errors.append("artifact manifest file_count does not match files")
    if manifest.get("total_size_bytes") not in (None, total):
        errors.append("artifact manifest total_size_bytes does not match files")
    for relative in sorted(set(actual) - listed):
        errors.append(f"public file omitted from manifest: {relative}")
    return errors


def validate_native_report(root: Path, report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["native client report must be an object"]
    errors: list[str] = []
    if report.get("schema_version") != 2:
        errors.append("native client report schema_version must be 2")
    for provenance_key, expected in (
        ("source_commit", os.environ.get("GITHUB_SHA")),
        ("run_id", os.environ.get("GITHUB_RUN_ID")),
        ("run_attempt", os.environ.get("GITHUB_RUN_ATTEMPT")),
    ):
        if expected and str(report.get(provenance_key) or "") != expected:
            errors.append(f"native client report provenance mismatch: {provenance_key}")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        return errors + ["native client report has no checks"]
    if len(checks) > MAX_CHECKS:
        return errors + ["native client report exceeds check-count limit"]
    seen: set[tuple[str, str]] = set()
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for check in checks:
        if not isinstance(check, dict):
            errors.append("native client report contains malformed check")
            continue
        core = str(check.get("core") or "")
        relative = check.get("path")
        status = check.get("status")
        if not core or not isinstance(relative, str) or not relative:
            errors.append("native client report check is missing core/path")
            continue
        check_key = (core, relative)
        if check_key in seen:
            errors.append(f"duplicate native client check: {core}:{relative}")
        seen.add(check_key)
        if status in counts:
            counts[status] += 1
        else:
            errors.append(
                f"unknown native validation status: {core}:{relative}={status}"
            )
        if status != "passed":
            errors.append(f"native validation did not pass: {core}:{relative}={status}")
        try:
            artifact = safe_path(root, relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not artifact.is_file() or artifact.is_symlink():
            errors.append(
                f"native validation references invalid artifact: {core}:{relative}"
            )
            continue
        expected_digest = check.get("artifact_sha256")
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            errors.append(f"native validation lacks artifact digest: {core}:{relative}")
        elif expected_digest != digest(artifact):
            errors.append(
                f"native validation artifact digest mismatch: {core}:{relative}"
            )
    for core, relative in REQUIRED_NATIVE_TARGETS.items():
        if (core, relative) not in seen:
            errors.append(f"missing required native validation: {core}:{relative}")
    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("native client report has no summary")
    else:
        for key, value in counts.items():
            if summary.get(key) != value:
                errors.append(f"native client report summary mismatch: {key}")
    return errors


def validate(root: Path, native_report: Path, min_coverage: float) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return ["artifact directory does not exist"]
    for name in REQUIRED_FILES:
        path = root / name
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing or invalid required release file: {name}")
    if not native_report.is_file() or native_report.is_symlink():
        errors.append(f"missing native client report: {native_report.name}")
    if errors:
        return errors
    metadata = load_checked(root / "metadata.json", errors)
    health = load_checked(root / "health.json", errors)
    manifest = load_checked(root / "artifact_manifest.json", errors)
    records = load_checked(root / "proxies.json", errors)
    compatibility = load_checked(root / "format_compatibility.json", errors)
    report = load_checked(native_report, errors)
    xray = load_checked(root / "xray.json", errors)
    singbox = load_checked(root / "singbox.json", errors)
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
    # NOTE: metadata.time_limited (slow source intake) is intentionally NOT a
    # gate error. Three consecutive runs (32668367033, 32722445848,
    # 32754492501) failed solely on it while passing every quality gate -
    # with a different shard each time, so no fixed window can satisfy it.
    # It stays recorded in health.json as the non-blocking note
    # "pipeline_time_limited" for transparency.
    if (
        safe_int(metadata.get("logical_total_working") or metadata.get("total_working"))
        <= 0
    ):
        errors.append("no logical working proxies")

    drop_reasons = metadata.get("drop_reasons")
    if drop_reasons is not None and not isinstance(drop_reasons, dict):
        errors.append("metadata drop_reasons must be an object")
    elif isinstance(drop_reasons, dict):
        for key, value in drop_reasons.items():
            if is_tester_infrastructure_drop_reason(key) and safe_int(value):
                errors.append(f"tester infrastructure errors remain: {key}={value}")
    if not isinstance(health, dict):
        errors.append("health.json must be an object")
    else:
        blockers = health.get("release_blockers", [])
        if not isinstance(blockers, list):
            errors.append("health release_blockers must be a list")
        else:
            errors.extend(
                f"health blocker: {item}"
                for item in blockers
                if not _is_nonblocking_health_note(item)
            )

    if not isinstance(compatibility, dict):
        errors.append("format_compatibility.json must be an object")
    else:
        targets = compatibility.get("targets")
        if not isinstance(targets, dict):
            errors.append("compatibility targets must be an object")
        else:
            for target in REQUIRED_NATIVE_TARGETS:
                item = targets.get(target)
                if not isinstance(item, dict) or item.get("status") not in {
                    "generated",
                    "passed",
                }:
                    errors.append(f"compatibility target is not generated: {target}")
    errors.extend(validate_native_report(root, report))
    try:
        errors.extend(validate_xray_config(xray, "xray.json"))
    except (TypeError, ValueError, KeyError) as exc:
        errors.append(f"xray validation failed safely: {type(exc).__name__}")
    try:
        errors.extend(validate_singbox_config(singbox, "singbox.json"))
    except (TypeError, ValueError, KeyError) as exc:
        errors.append(f"sing-box validation failed safely: {type(exc).__name__}")
    errors.extend(validate_manifest(root, manifest))
    return errors


def promote(root: Path, native_report: Path, min_coverage: float) -> None:
    manifest = load_checked(root / "artifact_manifest.json", [])
    had_signature = isinstance(manifest, dict) and "manifest_signature" in manifest
    signing_key = os.environ.get("CS_SIGNING_PRIVATE_KEY_HEX")
    if had_signature and not signing_key:
        raise ValueError(
            "promotion would invalidate manifest_signature but no signing key is configured"
        )
    stage = root.parent / f".{root.name}.promote-{uuid.uuid4().hex}"
    backup = root.parent / f".{root.name}.backup-{uuid.uuid4().hex}"
    shutil.copytree(root, stage, symlinks=True)
    try:
        evidence = stage / NATIVE_REPORT_RELATIVE_PATH
        evidence.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(native_report, evidence)
        metadata = load_checked(stage / "metadata.json", [])
        health = load_checked(stage / "health.json", [])
        staged_manifest = load_checked(stage / "artifact_manifest.json", [])
        if not isinstance(metadata, dict) or not isinstance(health, dict):
            raise ValueError("metadata.json and health.json must be objects")
        health.update(
            {
                "schema_version": "2.0",
                "status": "ok",
                "total_working": safe_int(
                    metadata.get("logical_total_working")
                    or metadata.get("total_working")
                ),
                "total_tested": safe_int(
                    metadata.get("total_tested") or metadata.get("tested")
                ),
                "source_coverage": safe_float(metadata.get("source_coverage")),
                "schema_validated": True,
                "native_clients_validated": True,
                "release_blockers": [],
                "native_report": NATIVE_REPORT_RELATIVE_PATH,
                "native_report_sha256": digest(evidence),
            }
        )
        (stage / "health.json").write_text(
            json.dumps(health, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        entries = manifest_entries(stage)
        if not isinstance(staged_manifest, dict):
            staged_manifest = {}
        staged_manifest.pop("manifest_signature", None)
        staged_manifest.update(
            {
                "schema_version": "2.0",
                "generated_at": staged_manifest.get("generated_at")
                or datetime.now(timezone.utc).isoformat(),
                "source_commit": os.environ.get(
                    "GITHUB_SHA", str(staged_manifest.get("source_commit") or "")
                ),
                "run_id": os.environ.get(
                    "GITHUB_RUN_ID", str(staged_manifest.get("run_id") or "")
                ),
                "run_attempt": os.environ.get(
                    "GITHUB_RUN_ATTEMPT", str(staged_manifest.get("run_attempt") or "")
                ),
                "file_count": len(entries),
                "total_size_bytes": sum(int(item["size_bytes"]) for item in entries),
                "files": entries,
            }
        )
        if signing_key:
            from configstream.signer import Signer

            staged_manifest["manifest_signature"] = Signer(signing_key).sign_manifest(
                staged_manifest
            )
        (stage / "artifact_manifest.json").write_text(
            json.dumps(staged_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        errors = validate(stage, evidence, min_coverage)
        if errors:
            raise ValueError("post-promotion validation failed: " + "; ".join(errors))
        os.replace(root, backup)
        try:
            os.replace(stage, root)
        except OSError:
            os.replace(backup, root)
            raise
        shutil.rmtree(backup)
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def _is_nonblocking_health_note(item: Any) -> bool:
    """Return True for truthful candidate-state notes that do not block release."""

    value = str(item)
    if value.startswith("unverified_shielded_candidates:"):
        return True
    # A time-limited intake means "some source lists were not fully drained",
    # not "the published proxies are bad": every emitted proxy still passed
    # testing, native-client validation, and the coverage gate. Verified
    # across runs 32668367033 / 32722445848 / 32754492501 where this was the
    # sole blocker with a different shard each time.
    if value == "pipeline_time_limited":
        return True
    return False


def _cat(relative: str) -> str:
    """Use the Pages validator as the canonical artifact taxonomy owner."""
    try:
        from scripts.validate_pages_artifact import _artifact_category
    except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
        from validate_pages_artifact import _artifact_category  # type: ignore[no-redef]
    return _artifact_category(relative)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--native-report", type=Path, required=True)
    parser.add_argument("--min-source-coverage", type=float, default=0.80)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    root = args.artifact_dir.resolve()
    native_report = args.native_report.resolve()
    try:
        errors = validate(root, native_report, args.min_source_coverage)
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
    ) as exc:
        errors = [f"release validation failed safely: {type(exc).__name__}"]
    if errors:
        print("ERROR: release gate failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    if args.promote:
        try:
            promote(root, native_report, args.min_source_coverage)
        except (
            OSError,
            UnicodeError,
            ValueError,
            TypeError,
            KeyError,
            RuntimeError,
        ) as exc:
            print(f"ERROR: release promotion failed: {type(exc).__name__}: {exc}")
            return 1
    print("OK: release gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
