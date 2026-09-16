# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run a bounded live ConfigStream merge against one of 1-2 admitted sources.

This script is intentionally read-only and publication-free. It exists for the
GitHub Actions live smoke check so pull requests exercise the real HTTPS fetch,
parse, normalize, deduplicate, and output-generation path without launching the
full production source matrix.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404 - fixed local Python entrypoint, no shell
import sys


def load_candidates(path: Path) -> list[str]:
    candidates = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not 1 <= len(candidates) <= 2:
        raise ValueError(f"live smoke requires 1-2 source candidates, found {len(candidates)}")
    if len(candidates) != len(set(candidates)):
        raise ValueError("live smoke source candidates must be unique")
    if any(not source.startswith("https://") for source in candidates):
        raise ValueError("live smoke source candidates must use HTTPS")
    return candidates


def output_is_usable(output_dir: Path) -> tuple[bool, str]:
    proxies_path = output_dir / "proxies.json"
    metadata_path = output_dir / "metadata.json"
    if not proxies_path.is_file() or not metadata_path.is_file():
        return False, "missing proxies.json or metadata.json"
    try:
        proxies = json.loads(proxies_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"invalid JSON output: {exc}"
    if not isinstance(proxies, list) or not proxies:
        return False, "proxies.json is empty or not a list"
    if not isinstance(metadata, dict):
        return False, "metadata.json is not an object"
    final_count = metadata.get("final_count", len(proxies))
    try:
        if int(final_count) < 1:
            return False, "metadata reports zero final proxies"
    except (TypeError, ValueError):
        return False, "metadata final_count is invalid"
    return True, f"generated {len(proxies)} proxies"


def _run_attempt(
    *,
    source: str,
    source_file: Path,
    output_dir: Path,
    max_workers: int,
    fetch_timeout: int,
    max_latency: int,
    attempt_timeout: int,
) -> tuple[int, str]:
    source_file.write_text(source + "\n", encoding="utf-8")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "configstream.cli",
        "merge",
        "--sources",
        str(source_file),
        "--output",
        str(output_dir),
        "--max-workers",
        str(max_workers),
        "--timeout",
        str(fetch_timeout),
        "--max-latency",
        str(max_latency),
    ]
    env = os.environ.copy()
    env.update(
        {
            "ENABLE_WASHER": "false",
            "ENABLE_WARP_REVIVAL": "false",
            "ENABLE_VWARP_REVIVAL": "false",
            "USE_VWARP_TUNNEL": "false",
            "FORCE_SCANNER": "false",
            "ALLOW_ACTIVE_SCANNING": "false",
        }
    )
    try:
        completed = subprocess.run(  # nosec B603 - argv is fixed except bounded values
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=attempt_timeout,
            check=False,
            env=env,
        )
        return completed.returncode, completed.stdout or ""
    except subprocess.TimeoutExpired as exc:
        captured = exc.stdout or ""
        if isinstance(captured, bytes):
            captured = captured.decode("utf-8", errors="replace")
        return 124, f"{captured}\nLive smoke attempt timed out after {attempt_timeout}s\n"


def run(args: argparse.Namespace) -> int:
    candidates = load_candidates(args.sources)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.selected_source.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text("", encoding="utf-8")
    if args.selected_source.exists():
        args.selected_source.unlink()

    source_file = args.output.parent / ".configstream-live-smoke-source.txt"
    failures: list[str] = []
    try:
        for index, source in enumerate(candidates, start=1):
            returncode, output = _run_attempt(
                source=source,
                source_file=source_file,
                output_dir=args.output,
                max_workers=args.max_workers,
                fetch_timeout=args.fetch_timeout,
                max_latency=args.max_latency,
                attempt_timeout=args.attempt_timeout,
            )
            with args.log.open("a", encoding="utf-8") as handle:
                handle.write(f"===== live smoke attempt {index}/{len(candidates)} =====\n")
                handle.write(f"source={source}\n")
                handle.write(output)
                if output and not output.endswith("\n"):
                    handle.write("\n")
                handle.write(f"exit_code={returncode}\n")

            if returncode != 0:
                failures.append(f"{source}: merge exited {returncode}")
                continue
            usable, reason = output_is_usable(args.output)
            if not usable:
                failures.append(f"{source}: {reason}")
                continue

            args.selected_source.write_text(source + "\n", encoding="utf-8")
            print(f"OK: live ConfigStream smoke succeeded with {source}: {reason}")
            return 0
    finally:
        source_file.unlink(missing_ok=True)

    print("ERROR: every bounded live smoke source failed", file=sys.stderr)
    for failure in failures:
        print(f"  - {failure}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--selected-source", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--fetch-timeout", type=int, default=15)
    parser.add_argument("--max-latency", type=int, default=6000)
    parser.add_argument("--attempt-timeout", type=int, default=240)
    args = parser.parse_args()
    if args.max_workers < 1 or args.max_workers > 2:
        parser.error("--max-workers must be between 1 and 2")
    if args.fetch_timeout < 1 or args.fetch_timeout > 30:
        parser.error("--fetch-timeout must be between 1 and 30 seconds")
    if args.attempt_timeout < 30 or args.attempt_timeout > 300:
        parser.error("--attempt-timeout must be between 30 and 300 seconds")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
