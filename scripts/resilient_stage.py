# SPDX-License-Identifier: AGPL-3.0-or-later
"""Resilient workflow stage execution and release readiness evidence.

This helper separates execution evidence from publication policy. Stage failures
are recorded; readiness decides whether canonical artifacts may be published.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import time
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = 2
SECRET_RE = re.compile(r"(?:TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY|STEGO_KEY|CONFIG_STREAM_KEY|JWT|CREDENTIAL|KEY)", re.I)

@dataclass(frozen=True)
class StageResult:
    schema_version: int
    name: str
    category: str
    criticality: str
    description: str
    remediation: str
    status: str
    exit_code: int
    started_at: str
    completed_at: str
    duration_seconds: float
    command: list[str]
    attempts: list[dict[str, Any]]
    failure_class: str | None = None
    error: str | None = None


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in value).strip("-") or "stage"


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def secrets_from_env(env: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(sorted({v for k, v in env.items() if v and SECRET_RE.search(k)}, key=len, reverse=True))


def redact(value: str, secrets: Sequence[str]) -> str:
    for secret in secrets:
        value = value.replace(secret, "***REDACTED***")
    return value


def write_result(report_dir: Path, result: StageResult) -> None:
    atomic_json(report_dir / f"{safe_name(result.name)}.json", asdict(result))
    print(f"{result.status}: {result.name} exit={result.exit_code}")


def record_stage(name: str, status: str, report_dir: Path, **kwargs: Any) -> StageResult:
    exit_code = int(kwargs.pop("exit_code", 0))
    if status == "failed" and exit_code == 0:
        exit_code = 1
    result = StageResult(
        schema_version=SCHEMA_VERSION,
        name=name,
        category=kwargs.pop("category", "external"),
        criticality=kwargs.pop("criticality", "diagnostic"),
        description=kwargs.pop("description", ""),
        remediation=kwargs.pop("remediation", ""),
        status=status,
        exit_code=exit_code,
        started_at=now(),
        completed_at=now(),
        duration_seconds=0.0,
        command=[],
        attempts=[],
        failure_class=kwargs.pop("failure_class", None),
        error=kwargs.pop("error", None),
    )
    write_result(report_dir, result)
    return result


def run_stage(name: str, command: Sequence[str], report_dir: Path, **kwargs: Any) -> StageResult:
    report_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    secrets = secrets_from_env(env)
    started = time.monotonic()
    started_at = now()
    log = report_dir / f"{safe_name(name)}.log"
    try:
        with log.open("w", encoding="utf-8") as handle:
            handle.write("$ " + shlex.join(redact(str(x), secrets) for x in command) + "\n")
            proc = subprocess.run(list(command), stdout=handle, stderr=subprocess.STDOUT, text=True, check=False, env=env, timeout=kwargs.get("timeout"))
        code = int(proc.returncode)
        failure = None if code == 0 else "nonzero_exit"
        error = None if code == 0 else f"command exited with status {code}"
    except subprocess.TimeoutExpired:
        code, failure, error = 124, "timeout", "stage timeout"
    except OSError as exc:
        code, failure, error = 127, "execution_error", str(exc)
    result = StageResult(
        schema_version=SCHEMA_VERSION,
        name=name,
        category=kwargs.get("category", "general"),
        criticality=kwargs.get("criticality", "required"),
        description=kwargs.get("description", ""),
        remediation=kwargs.get("remediation", ""),
        status="success" if code == 0 else "failed",
        exit_code=code,
        started_at=started_at,
        completed_at=now(),
        duration_seconds=round(time.monotonic() - started, 3),
        command=[redact(str(x), secrets) for x in command],
        attempts=[{"log": str(log), "exit_code": code}],
        failure_class=failure,
        error=error,
    )
    write_result(report_dir, result)
    return result


def evaluate_readiness(report_dir: Path, required_stages: Iterable[str], required_files: Iterable[Path], output: Path) -> dict[str, Any]:
    blockers=[]
    for stage in required_stages:
        payload=json.loads((report_dir / f"{safe_name(stage)}.json").read_text()) if (report_dir / f"{safe_name(stage)}.json").exists() else None
        if not payload or payload.get("status") != "success":
            blockers.append(stage)
    for path in required_files:
        if not path.is_file() or path.stat().st_size == 0:
            blockers.append(str(path))
    result={"schema_version": SCHEMA_VERSION, "publish_ready": not blockers, "status": "ready" if not blockers else "degraded", "blockers": blockers}
    atomic_json(output, result)
    print(json.dumps(result, indent=2))
    return result


def context(output: Path) -> None:
    atomic_json(output, {"schema_version": SCHEMA_VERSION, "generated_at": now(), "python": platform.python_version(), "repository": os.getenv("GITHUB_REPOSITORY")})


def summary(report_dir: Path, output: Path) -> None:
    stages=[json.loads(p.read_text()) for p in report_dir.glob("*.json")]
    atomic_json(output, {"schema_version": SCHEMA_VERSION, "stages": stages})


def main(argv=None) -> int:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="cmd", required=True)
    run=sub.add_parser("run"); run.add_argument("--name", required=True); run.add_argument("--report-dir", type=Path, default=Path("pipeline-evidence/stages")); run.add_argument("command", nargs=argparse.REMAINDER)
    rec=sub.add_parser("record"); rec.add_argument("--name", required=True); rec.add_argument("--status", required=True); rec.add_argument("--report-dir", type=Path, default=Path("pipeline-evidence/stages"))
    ctx=sub.add_parser("context"); ctx.add_argument("--output", type=Path, default=Path("pipeline-evidence/workflow_context.json"))
    summ=sub.add_parser("summary"); summ.add_argument("--report-dir", type=Path, default=Path("pipeline-evidence/stages")); summ.add_argument("--output", type=Path, default=Path("pipeline-evidence/stage_summary.json"))
    ev=sub.add_parser("evaluate"); ev.add_argument("--report-dir", type=Path, default=Path("pipeline-evidence/stages")); ev.add_argument("--required-stage", action="append", default=[]); ev.add_argument("--required-file", type=Path, action="append", default=[]); ev.add_argument("--output", type=Path, default=Path("pipeline-evidence/release_readiness.json"))
    a=parser.parse_args(argv)
    if a.cmd=="run":
        run_stage(a.name, a.command[1:] if a.command and a.command[0]=="--" else a.command, a.report_dir)
    elif a.cmd=="record": record_stage(a.name, a.status, a.report_dir)
    elif a.cmd=="context": context(a.output)
    elif a.cmd=="summary": summary(a.report_dir, a.output)
    else: evaluate_readiness(a.report_dir, a.required_stage, a.required_file, a.output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
