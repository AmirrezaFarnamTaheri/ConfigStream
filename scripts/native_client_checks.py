# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run mandatory native client validation and emit structured evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil

# Native validators are resolved with shutil.which and invoked with fixed
# argument lists. No shell or user-controlled command text is used.
import subprocess  # nosec B404
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_TARGETS = {
    "sing-box": "singbox.json",
    "mihomo": "clash.yaml",
    "xray": "xray.json",
}


def sha256_file(path: Path) -> str | None:
    """Return the SHA-256 digest for *path*, or ``None`` when it is absent."""
    if not path.is_file() or path.is_symlink():
        return None
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def artifact_path(path: Path, root: Path) -> str:
    """Return a stable POSIX path relative to the validated artifact root."""
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"native-check target escapes artifact root: {path}") from exc


def run(
    command: list[str],
    display_command: list[str],
    core: str,
    path: Path,
    artifact_root: Path,
) -> dict[str, Any]:
    """Run one native check and bind the result to the exact artifact bytes."""
    relative = artifact_path(path, artifact_root)
    artifact_sha256 = sha256_file(path)
    try:
        # Commands are assembled exclusively from shutil.which results, fixed
        # flags, and repository-controlled artifact paths. shell=False is the
        # subprocess default and no user-provided command text is evaluated.
        result = subprocess.run(  # nosec B603
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "core": core,
            "path": relative,
            "artifact_sha256": artifact_sha256,
            "status": "failed",
            "command": display_command,
            "error": str(exc),
        }
    output = (result.stderr or result.stdout or "").strip()
    if len(output) > 1000:
        output = output[:1000] + "...[truncated]"
    return {
        "core": core,
        "path": relative,
        "artifact_sha256": artifact_sha256,
        "status": "passed" if result.returncode == 0 else "failed",
        "command": display_command,
        "error": None if result.returncode == 0 else output,
    }


def missing_validator_check(core: str, target: Path, artifact_root: Path) -> dict[str, Any]:
    """Return deterministic failed evidence for a missing required validator."""
    return {
        "core": core,
        "path": artifact_path(target, artifact_root),
        "artifact_sha256": sha256_file(target),
        "status": "failed",
        "command": None,
        "error": "required native validator binary is unavailable",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    artifact_root = args.artifact_dir.resolve()
    binaries = {
        "sing-box": shutil.which("sing-box"),
        "mihomo": shutil.which("mihomo") or shutil.which("clash-meta"),
        "xray": shutil.which("xray"),
    }
    checks: list[dict[str, Any]] = []

    sing_box = binaries["sing-box"]
    if sing_box:
        sing_box_name = Path(sing_box).name
        for path in sorted(artifact_root.glob("singbox*.json")):
            relative = artifact_path(path, artifact_root)
            checks.append(
                run(
                    [sing_box, "check", "-c", str(path)],
                    [sing_box_name, "check", "-c", relative],
                    "sing-box",
                    path,
                    artifact_root,
                )
            )
    else:
        checks.append(
            missing_validator_check(
                "sing-box", artifact_root / REQUIRED_TARGETS["sing-box"], artifact_root
            )
        )

    mihomo = binaries["mihomo"]
    if mihomo:
        mihomo_name = Path(mihomo).name
        for path in sorted(artifact_root.glob("clash*.yaml")):
            relative = artifact_path(path, artifact_root)
            checks.append(
                run(
                    [mihomo, "-t", "-f", str(path)],
                    [mihomo_name, "-t", "-f", relative],
                    "mihomo",
                    path,
                    artifact_root,
                )
            )
    else:
        checks.append(
            missing_validator_check(
                "mihomo", artifact_root / REQUIRED_TARGETS["mihomo"], artifact_root
            )
        )

    xray = binaries["xray"]
    xray_config = artifact_root / REQUIRED_TARGETS["xray"]
    if xray and xray_config.is_file():
        xray_name = Path(xray).name
        relative = artifact_path(xray_config, artifact_root)
        checks.append(
            run(
                [xray, "run", "-test", "-config", str(xray_config)],
                [xray_name, "run", "-test", "-config", relative],
                "xray",
                xray_config,
                artifact_root,
            )
        )
    elif not xray:
        checks.append(missing_validator_check("xray", xray_config, artifact_root))
    else:
        checks.append(
            {
                "core": "xray",
                "path": REQUIRED_TARGETS["xray"],
                "artifact_sha256": None,
                "status": "failed",
                "command": [Path(xray).name, "run", "-test", "-config", "xray.json"],
                "error": "required native validation target is unavailable",
            }
        )

    summary = {
        "passed": sum(item.get("status") == "passed" for item in checks),
        "failed": sum(item.get("status") == "failed" for item in checks),
        "skipped": sum(item.get("status") == "skipped" for item in checks),
    }
    report = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "tools": {
            name: {
                "available": bool(binary),
                "command": Path(binary).name if binary else None,
            }
            for name, binary in binaries.items()
        },
        "checks": checks,
        "summary": summary,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if summary["failed"] or summary["skipped"] or not checks:
        print(json.dumps(summary))
        return 1
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
