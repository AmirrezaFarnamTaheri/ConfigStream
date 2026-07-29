# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run workflow stages without masking later diagnostics.

A stage failure is recorded as structured evidence and returned to the caller as
an output, while this helper itself exits successfully.  A separate evaluation
step decides whether a candidate is safe to publish.  This keeps GitHub Actions
running through partial and environmental failures without weakening release
integrity: failed mandatory gates block publication, not evidence collection.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    exit_code: int
    duration_seconds: float
    command: list[str]
    log_file: str
    error: str | None = None


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _append_github_output(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _append_summary(markdown: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write(markdown.rstrip() + "\n")


def _safe_name(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in "-_" else "-" for character in value)
    cleaned = cleaned.strip("-")
    return cleaned or "stage"


def run_stage(
    name: str,
    command: Sequence[str],
    report_dir: Path,
    *,
    timeout: float | None = None,
    cwd: Path | None = None,
) -> StageResult:
    report_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_name(name)
    log_path = report_dir / f"{safe_name}.log"
    report_path = report_dir / f"{safe_name}.json"
    started = time.monotonic()
    exit_code = 127
    error: str | None = None

    try:
        with log_path.open("w", encoding="utf-8") as log_handle:
            log_handle.write(f"$ {shlex.join(command)}\n")
            log_handle.flush()
            completed = subprocess.run(
                list(command),
                cwd=str(cwd) if cwd else None,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                check=False,
                env=os.environ.copy(),
            )
            exit_code = int(completed.returncode)
    except subprocess.TimeoutExpired:
        exit_code = 124
        error = f"stage exceeded timeout of {timeout} seconds"
        with log_path.open("a", encoding="utf-8") as log_handle:
            log_handle.write(f"\nTIMEOUT: {error}\n")
    except OSError as exc:
        exit_code = 127
        error = f"could not execute stage: {exc}"
        with log_path.open("a", encoding="utf-8") as log_handle:
            log_handle.write(f"\nEXECUTION ERROR: {error}\n")

    duration = round(time.monotonic() - started, 3)
    status = "success" if exit_code == 0 else "failed"
    result = StageResult(
        name=name,
        status=status,
        exit_code=exit_code,
        duration_seconds=duration,
        command=list(command),
        log_file=str(log_path),
        error=error,
    )
    _atomic_json(report_path, asdict(result))
    _append_github_output(
        {
            "status": status,
            "exit_code": str(exit_code),
            "report": str(report_path),
            "log": str(log_path),
        }
    )
    icon = "✅" if status == "success" else "⚠️"
    _append_summary(
        f"- {icon} **{name}**: `{status}` (exit `{exit_code}`, {duration:.3f}s)"
    )
    print(f"{icon} {name}: {status} (exit={exit_code}, duration={duration:.3f}s)")
    if error:
        print(error)
    return result


def _load_stage(report_dir: Path, name: str) -> dict[str, object] | None:
    path = report_dir / f"{_safe_name(name)}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def evaluate_readiness(
    report_dir: Path,
    required_stages: Iterable[str],
    required_files: Iterable[Path],
    output_path: Path,
) -> dict[str, object]:
    required = list(dict.fromkeys(required_stages))
    files = list(dict.fromkeys(required_files))
    blockers: list[str] = []
    stages: dict[str, dict[str, object] | None] = {}

    for name in required:
        stage = _load_stage(report_dir, name)
        stages[name] = stage
        if stage is None:
            blockers.append(f"missing stage report: {name}")
        elif stage.get("status") != "success":
            blockers.append(
                f"stage failed: {name} (exit {stage.get('exit_code', 'unknown')})"
            )

    for path in files:
        if not path.is_file() or path.stat().st_size <= 0:
            blockers.append(f"required release file missing or empty: {path}")

    publish_ready = not blockers
    payload: dict[str, object] = {
        "publish_ready": publish_ready,
        "status": "ready" if publish_ready else "degraded",
        "required_stages": required,
        "required_files": [str(path) for path in files],
        "blockers": blockers,
        "stages": stages,
    }
    _atomic_json(output_path, payload)
    _append_github_output(
        {
            "publish_ready": "true" if publish_ready else "false",
            "status": str(payload["status"]),
            "report": str(output_path),
        }
    )

    if publish_ready:
        _append_summary("\n### Release readiness\n✅ Candidate passed every mandatory gate and may be published.")
        print("✅ release candidate is ready for publication")
    else:
        lines = "\n".join(f"- {blocker}" for blocker in blockers)
        _append_summary(
            "\n### Release readiness\n"
            "⚠️ Candidate is degraded. Publication was skipped, but diagnostics and evidence remain available.\n"
            f"{lines}"
        )
        print("⚠️ release candidate is degraded; publication must be skipped")
        for blocker in blockers:
            print(f"  - {blocker}")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    run_parser = subparsers.add_parser("run", help="Run one stage and always preserve a report")
    run_parser.add_argument("--name", required=True)
    run_parser.add_argument("--report-dir", type=Path, default=Path("pipeline-evidence/stages"))
    run_parser.add_argument("--timeout", type=float)
    run_parser.add_argument("--cwd", type=Path)
    run_parser.add_argument("command", nargs=argparse.REMAINDER)

    evaluate_parser = subparsers.add_parser(
        "evaluate", help="Evaluate whether mandatory stages produced a publishable candidate"
    )
    evaluate_parser.add_argument("--report-dir", type=Path, default=Path("pipeline-evidence/stages"))
    evaluate_parser.add_argument("--required-stage", action="append", default=[])
    evaluate_parser.add_argument("--required-file", type=Path, action="append", default=[])
    evaluate_parser.add_argument(
        "--output", type=Path, default=Path("pipeline-evidence/release_readiness.json")
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.action == "run":
        command = list(args.command)
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            parser.error("run requires a command after --")
        run_stage(
            args.name,
            command,
            args.report_dir,
            timeout=args.timeout,
            cwd=args.cwd,
        )
        return 0

    evaluate_readiness(
        args.report_dir,
        args.required_stage,
        args.required_file,
        args.output,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
