# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run mandatory native client validation and emit bounded evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess  # nosec B404
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from configstream.security_validator import SecurityValidator

try:
    from scripts.public_client_configs import (
        discover_mihomo_configs,
        discover_singbox_configs,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from public_client_configs import (  # type: ignore[no-redef]
        discover_mihomo_configs,
        discover_singbox_configs,
    )

MAX_OUTPUT_CHARS = 1000


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def safe_artifact(root: Path, path: Path) -> tuple[Path | None, str | None]:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        return None, f"artifact is unavailable: {type(exc).__name__}"
    if not resolved.is_relative_to(root):
        return None, "artifact path escapes the release root"
    if path.is_symlink():
        return None, "artifact path is a symlink"
    return resolved, None


def run(
    root: Path,
    command: list[str],
    core: str,
    path: Path,
    binary_digest: str,
) -> dict[str, Any]:
    resolved, path_error = safe_artifact(root, path)
    relative = (
        path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
    )
    base: dict[str, Any] = {
        "core": core,
        "path": relative,
        "status": "failed",
        "command": [
            Path(command[0]).name,
            *[relative if item == str(path) else item for item in command[1:]],
        ],
        "artifact_sha256": None,
        "binary_sha256": binary_digest,
        "error": path_error,
    }
    if resolved is None:
        return base
    before = digest(resolved)
    base["artifact_sha256"] = before
    with tempfile.TemporaryDirectory(prefix=f"configstream-{core}-") as home:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": home,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "TZ": "UTC",
            "NO_COLOR": "1",
        }
        try:
            result = subprocess.run(  # nosec B603
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=60,
                cwd=root,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            base["error"] = type(exc).__name__
            return base
    after = digest(resolved)
    if before != after:
        base["error"] = "artifact changed during native validation"
        return base
    output = (result.stderr or result.stdout or "").strip()
    output = SecurityValidator.sanitize_log_message(output)
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "...[truncated]"
    base["status"] = "passed" if result.returncode == 0 else "failed"
    base["error"] = None if result.returncode == 0 else output
    return base


def missing_artifact(core: str, relative: str, binary_digest: str) -> dict[str, Any]:
    return {
        "core": core,
        "path": relative,
        "status": "failed",
        "command": None,
        "artifact_sha256": None,
        "binary_sha256": binary_digest,
        "error": "required native artifact is unavailable",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = args.artifact_dir.resolve()
    checks: list[dict[str, Any]] = []
    binary_values = {
        "sing-box": shutil.which("sing-box"),
        "mihomo": shutil.which("mihomo") or shutil.which("clash-meta"),
        "xray": shutil.which("xray"),
    }
    binaries = {
        name: Path(value).resolve() if value else None
        for name, value in binary_values.items()
    }
    for core, binary in binaries.items():
        if binary is None:
            checks.append(
                {
                    "core": core,
                    "path": _required_native_target(core),
                    "status": "failed",
                    "command": None,
                    "artifact_sha256": None,
                    "binary_sha256": None,
                    "error": "required native validator binary is unavailable",
                }
            )
    binary_digests = {
        name: digest(binary) if binary is not None else None
        for name, binary in binaries.items()
    }

    singbox_binary = binaries["sing-box"]
    singbox_digest = binary_digests["sing-box"]
    if singbox_binary is not None and singbox_digest is not None:
        singbox_paths = discover_singbox_configs(root)
        if not singbox_paths:
            checks.append(missing_artifact("sing-box", "singbox.json", singbox_digest))
        for path in singbox_paths:
            checks.append(
                run(
                    root,
                    [str(singbox_binary), "check", "-c", str(path)],
                    "sing-box",
                    path,
                    singbox_digest,
                )
            )

    mihomo_binary = binaries["mihomo"]
    mihomo_digest = binary_digests["mihomo"]
    if mihomo_binary is not None and mihomo_digest is not None:
        mihomo_paths = discover_mihomo_configs(root)
        if not mihomo_paths:
            checks.append(missing_artifact("mihomo", "clash.yaml", mihomo_digest))
        for path in mihomo_paths:
            checks.append(
                run(
                    root,
                    [str(mihomo_binary), "-t", "-f", str(path)],
                    "mihomo",
                    path,
                    mihomo_digest,
                )
            )

    xray_binary = binaries["xray"]
    xray_digest = binary_digests["xray"]
    xray_path = root / "xray.json"
    if xray_binary is not None and xray_digest is not None:
        if xray_path.is_file() and not xray_path.is_symlink():
            checks.append(
                run(
                    root,
                    [str(xray_binary), "run", "-test", "-config", str(xray_path)],
                    "xray",
                    xray_path,
                    xray_digest,
                )
            )
        else:
            checks.append(missing_artifact("xray", "xray.json", xray_digest))
    summary = {
        "passed": sum(item["status"] == "passed" for item in checks),
        "failed": sum(item["status"] == "failed" for item in checks),
        "skipped": sum(item["status"] == "skipped" for item in checks),
    }
    report = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "tools": {
            name: {
                "available": binary is not None,
                "binary": binary.name if binary else None,
                "binary_sha256": binary_digests[name],
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
    print(json.dumps(summary))
    return 1 if summary["failed"] or summary["skipped"] or not checks else 0


def _required_native_target(core: str) -> str:
    return {
        "sing-box": "singbox.json",
        "mihomo": "clash.yaml",
        "xray": "xray.json",
    }[core]


if __name__ == "__main__":
    raise SystemExit(main())
