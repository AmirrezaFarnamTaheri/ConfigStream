# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run mandatory native client validation and emit structured evidence."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run(command: list[str], core: str, path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "core": core,
            "path": path.name,
            "status": "failed",
            "command": command,
            "error": str(exc),
        }
    output = (result.stderr or result.stdout or "").strip()
    if len(output) > 1000:
        output = output[:1000] + "...[truncated]"
    return {
        "core": core,
        "path": path.name,
        "status": "passed" if result.returncode == 0 else "failed",
        "command": command,
        "error": None if result.returncode == 0 else output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    binaries = {
        "sing-box": shutil.which("sing-box"),
        "mihomo": shutil.which("mihomo") or shutil.which("clash-meta"),
        "xray": shutil.which("xray"),
    }
    missing = [name for name, path in binaries.items() if not path]
    checks: list[dict[str, Any]] = []
    if missing:
        for core in missing:
            checks.append(
                {
                    "core": core,
                    "path": None,
                    "status": "failed",
                    "command": None,
                    "error": "required native validator binary is unavailable",
                }
            )
    if binaries["sing-box"]:
        for path in sorted(args.artifact_dir.glob("singbox*.json")):
            checks.append(run([binaries["sing-box"], "check", "-c", str(path)], "sing-box", path))
    if binaries["mihomo"]:
        for path in sorted(args.artifact_dir.glob("clash*.yaml")):
            checks.append(run([binaries["mihomo"], "-t", "-f", str(path)], "mihomo", path))
    xray_config = args.artifact_dir / "xray.json"
    if binaries["xray"] and xray_config.is_file():
        checks.append(run([binaries["xray"], "run", "-test", "-config", str(xray_config)], "xray", xray_config))

    summary = {
        "passed": sum(item["status"] == "passed" for item in checks),
        "failed": sum(item["status"] == "failed" for item in checks),
        "skipped": sum(item["status"] == "skipped" for item in checks),
    }
    report = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tools": {
            name: {"available": bool(path), "binary": path}
            for name, path in binaries.items()
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
