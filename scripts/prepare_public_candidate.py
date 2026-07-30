# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build a public candidate transactionally from merged data and static assets."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _copy_optional(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return True


def prepare(
    merged_output: Path,
    frontend: Path,
    destination: Path,
    repo_root: Path,
) -> dict[str, object]:
    if not merged_output.is_dir():
        raise FileNotFoundError(f"merged output directory not found: {merged_output}")
    if not frontend.is_dir():
        raise FileNotFoundError(f"frontend directory not found: {frontend}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = destination.parent
    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}-staging-", dir=staging_parent
    ) as temporary:
        staging = Path(temporary) / destination.name
        shutil.copytree(merged_output, staging)
        shutil.copytree(frontend, staging, dirs_exist_ok=True)
        copied_optional = {
            "wiki": _copy_optional(
                repo_root / "docs" / "wiki", staging / "docs" / "wiki"
            ),
            "lab_scanner": _copy_optional(
                repo_root / "tools" / "lab-scanner.py",
                staging / "tools" / "lab-scanner.py",
            ),
            "lab_runner": _copy_optional(
                repo_root / "tools" / "lab-runner.sh",
                staging / "tools" / "lab-runner.sh",
            ),
        }
        (staging / "api").mkdir(parents=True, exist_ok=True)
        for source_name, destination_name in (
            ("proxies.json", "proxies"),
            ("metadata.json", "stats"),
        ):
            source = staging / source_name
            if source.is_file():
                shutil.copy2(source, staging / "api" / destination_name)
        (staging / ".nojekyll").touch()
        cache = staging / "data" / "test_cache.json"
        if cache.exists():
            cache.unlink()
        events = staging / "pipeline_events.jsonl"
        if not events.is_file() or events.stat().st_size == 0:
            events.write_text(
                json.dumps(
                    {
                        "timestamp": datetime.now(timezone.utc)
                        .isoformat()
                        .replace("+00:00", "Z"),
                        "stage": "artifact_prepare",
                        "level": "info",
                        "event_type": "artifact_prepare",
                        "message": "public candidate created transactionally",
                    },
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )

        backup = destination.with_name(destination.name + ".previous")
        if backup.exists():
            shutil.rmtree(backup)
        moved_previous = False
        try:
            if destination.exists():
                destination.replace(backup)
                moved_previous = True
            staging.replace(destination)
        except Exception:
            if not destination.exists() and moved_previous and backup.exists():
                backup.replace(destination)
            raise
        else:
            if backup.exists():
                shutil.rmtree(backup)

    payload = {
        "destination": str(destination),
        "files": sum(1 for path in destination.rglob("*") if path.is_file()),
        "copied_optional": copied_optional,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("merged_output", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--frontend", type=Path, default=Path("frontend"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    prepare(args.merged_output, args.frontend, args.destination, args.repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
