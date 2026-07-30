# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run workflow stages without losing evidence, then evaluate publish readiness.

The CLI deliberately separates command execution from publication policy. A
stage command may fail while later diagnostic steps continue; the final
``evaluate`` command is the fail-closed authority for canonical publication.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import queue
import re
import shlex

# Command execution is this tool's explicit purpose.
import subprocess  # nosec B404
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, TextIO, Tuple

SCHEMA_VERSION = 3
DEFAULT_TIMEOUT_SECONDS = 900.0
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = REPO_ROOT / "pipeline-evidence" / "stages"
DEFAULT_CONTEXT_OUTPUT = REPO_ROOT / "pipeline-evidence" / "workflow_context.json"
DEFAULT_SUMMARY_OUTPUT = REPO_ROOT / "pipeline-evidence" / "stage_summary.json"
DEFAULT_READINESS_OUTPUT = REPO_ROOT / "pipeline-evidence" / "release_readiness.json"
SAFE_STAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
CANONICAL_STATUSES = frozenset({"success", "failed", "skipped"})
SECRET_NAME_RE = re.compile(
    r"(?:TOKEN|SECRET|PASSWORD|PASS|API_KEY|PRIVATE_KEY|SIGNING|STEGO_KEY|"
    r"CONFIG_STREAM_KEY|JWT|CREDENTIAL|GDRIVE|SA_JSON|AUTH|COOKIE|SESSION|KEY)",
    re.IGNORECASE,
)
INLINE_SECRET_RE = re.compile(
    r"(?i)\b(token|access_token|api_key|apikey|secret|password|pass|authorization|auth)"
    r"\s*[:=]\s*([^\s,;]+)"
)
BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
URL_USERINFO_RE = re.compile(r"(?P<prefix>://[^/?#\s:@]+):([^/?#\s:@]+)@")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StageResult:
    """Serializable evidence for one logical workflow stage."""

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
    command: List[str]
    attempts: List[Dict[str, Any]]
    failure_class: Optional[str] = None
    error: Optional[str] = None


def now() -> str:
    """Return an RFC3339 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_name(value: str) -> str:
    """Validate and return a collision-free filesystem-safe stage name."""

    if not SAFE_STAGE_NAME_RE.fullmatch(value):
        raise ValueError("stage names must match ^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
    return value


def atomic_json(path: Path, payload: object) -> None:
    """Write JSON atomically so interrupted jobs never leave partial evidence."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def secrets_from_env(env: Mapping[str, str]) -> Tuple[str, ...]:
    """Collect non-empty environment values whose names are credential-shaped."""

    return tuple(
        sorted(
            {
                value
                for name, value in env.items()
                if value and len(value) >= 4 and SECRET_NAME_RE.search(name)
            },
            key=len,
            reverse=True,
        )
    )


def _project_sanitize(value: str) -> str:
    """Use the project sanitizer when importable, otherwise use a safe fallback."""

    try:
        from configstream.security_validator import SecurityValidator

        return SecurityValidator.sanitize_log_message(value)
    except Exception as exc:
        logger.warning(
            "Project log sanitizer unavailable; using local fallback (%s)",
            type(exc).__name__,
        )
        sanitized = URL_USERINFO_RE.sub(r"\g<prefix>:[MASKED]@", value)
        sanitized = BEARER_RE.sub("Bearer [MASKED]", sanitized)
        return INLINE_SECRET_RE.sub(r"\1=[MASKED]", sanitized)


def redact(value: str, secrets: Sequence[str]) -> str:
    """Remove known environment secrets and generic credential-shaped values."""

    sanitized = value
    for secret in secrets:
        sanitized = sanitized.replace(secret, "***REDACTED***")
    return _project_sanitize(sanitized)


def normalize_status(status: str) -> str:
    """Normalize GitHub outcomes and readiness aliases to stage statuses."""

    normalized = status.strip().lower()
    if normalized in {"success", "succeeded", "ready", "passed", "pass"}:
        return "success"
    if normalized in {"skipped", "skip", "not_run", "not-run", "neutral"}:
        return "skipped"
    if normalized in {
        "failure",
        "failed",
        "cancelled",
        "canceled",
        "timed_out",
        "timeout",
        "degraded",
        "error",
    }:
        return "failed"
    raise ValueError(f"unsupported stage status: {status!r}")


def validate_stage_report(payload: object, expected_name: str) -> Tuple[bool, str]:
    """Validate evidence identity, schema, status, and exit-code consistency."""

    if not isinstance(payload, dict):
        return False, "payload-not-object"
    if payload.get("schema_version") != SCHEMA_VERSION:
        return False, "schema-version"
    if payload.get("name") != expected_name:
        return False, "stage-name"
    status = payload.get("status")
    if not isinstance(status, str) or status not in CANONICAL_STATUSES:
        return False, "status"
    exit_code = payload.get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        return False, "exit-code-type"
    if status in {"success", "skipped"} and exit_code != 0:
        return False, "contradictory-exit-code"
    if status == "failed" and exit_code == 0:
        return False, "contradictory-exit-code"
    return True, status


def write_result(report_dir: Path, result: StageResult) -> None:
    """Persist one result and print a concise, non-sensitive status line."""

    atomic_json(report_dir / f"{safe_name(result.name)}.json", asdict(result))
    print(f"{result.status}: {result.name} exit={result.exit_code}")


def record_stage(
    name: str,
    status: str,
    report_dir: Path,
    *,
    category: str = "external",
    criticality: str = "diagnostic",
    description: str = "",
    remediation: str = "",
    exit_code: int = 0,
    failure_class: Optional[str] = None,
    error: Optional[str] = None,
) -> StageResult:
    """Record an externally executed action or an intentional skip."""

    safe_name(name)
    normalized = normalize_status(status)
    effective_exit_code = int(exit_code)
    if normalized == "failed" and effective_exit_code == 0:
        effective_exit_code = 1
    if normalized in {"success", "skipped"} and effective_exit_code != 0:
        raise ValueError(
            f"{normalized} evidence requires exit_code=0, got {effective_exit_code}"
        )
    result = StageResult(
        schema_version=SCHEMA_VERSION,
        name=name,
        category=category,
        criticality=criticality,
        description=description,
        remediation=remediation,
        status=normalized,
        exit_code=effective_exit_code,
        started_at=now(),
        completed_at=now(),
        duration_seconds=0.0,
        command=[],
        attempts=[],
        failure_class=failure_class,
        error=error,
    )
    write_result(report_dir, result)
    return result


def _stream_output(
    stream: TextIO,
    log_handle: TextIO,
    secrets: Sequence[str],
    errors: "queue.Queue[BaseException]",
) -> None:
    """Sanitize child output before writing it to either console or evidence."""

    try:
        for line in iter(stream.readline, ""):
            safe_line = redact(line, secrets)
            log_handle.write(safe_line)
            log_handle.flush()
            sys.stdout.write(safe_line)
            sys.stdout.flush()
    except BaseException as exc:  # pragma: no cover - defensive reader boundary
        logger.error("Stage output reader failed (%s)", type(exc).__name__)
        errors.put(exc)
    finally:
        stream.close()


def _run_attempt(
    command: Sequence[str],
    log_path: Path,
    env: Mapping[str, str],
    secrets: Sequence[str],
    timeout: float,
) -> Tuple[int, Optional[str], Optional[str]]:
    """Execute one bounded attempt while preserving sanitized live output."""

    reader_errors: "queue.Queue[BaseException]" = queue.Queue()
    try:
        with log_path.open("w", encoding="utf-8") as log_handle:
            command_line = "$ " + shlex.join(
                redact(str(argument), secrets) for argument in command
            )
            log_handle.write(command_line + "\n")
            log_handle.flush()
            print(command_line)
            # argv is intentionally executed without a shell.
            process = subprocess.Popen(  # nosec B603
                list(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=dict(env),
                bufsize=1,
            )
            if process.stdout is None:
                process.kill()
                process.wait(timeout=10)
                return 125, "log_stream_error", "subprocess stdout pipe was not created"
            reader = threading.Thread(
                target=_stream_output,
                args=(process.stdout, log_handle, secrets, reader_errors),
                daemon=True,
            )
            reader.start()
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                reader.join(timeout=10)
                return 124, "timeout", f"stage exceeded {timeout:g} seconds"
            reader.join(timeout=10)
            if reader.is_alive():
                return 125, "log_stream_error", "output reader did not terminate"
            if not reader_errors.empty():
                error = reader_errors.get()
                return 125, "log_stream_error", redact(str(error), secrets)
            code = int(return_code)
            if code == 0:
                return 0, None, None
            return code, "nonzero_exit", f"command exited with status {code}"
    except OSError as exc:
        return 127, "execution_error", redact(str(exc), secrets)


def run_stage(
    name: str,
    command: Sequence[str],
    report_dir: Path,
    *,
    category: str = "general",
    criticality: str = "required",
    description: str = "",
    remediation: str = "",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = 0,
    retry_backoff: float = 5.0,
) -> StageResult:
    """Run a bounded command, retain every attempt, and always return evidence."""

    safe_name(name)
    if not command:
        raise ValueError("stage command must not be empty")
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    if retries < 0:
        raise ValueError("retries must be non-negative")
    if retry_backoff < 0:
        raise ValueError("retry backoff must be non-negative")

    report_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    secrets = secrets_from_env(env)
    started = time.monotonic()
    started_at = now()
    attempts: List[Dict[str, Any]] = []
    code = 127
    failure: Optional[str] = "execution_error"
    error: Optional[str] = "stage was not attempted"

    for attempt_number in range(1, retries + 2):
        attempt_started = now()
        suffix = "" if retries == 0 else f"-attempt-{attempt_number}"
        log_path = report_dir / f"{safe_name(name)}{suffix}.log"
        code, failure, error = _run_attempt(command, log_path, env, secrets, timeout)
        attempts.append(
            {
                "attempt": attempt_number,
                "started_at": attempt_started,
                "completed_at": now(),
                "log": str(log_path),
                "exit_code": code,
                "failure_class": failure,
            }
        )
        if code == 0:
            break
        if attempt_number <= retries:
            delay = retry_backoff * (2 ** (attempt_number - 1))
            print(
                f"retrying {name} after exit={code}; "
                f"attempt={attempt_number + 1}/{retries + 1}; delay={delay:g}s"
            )
            time.sleep(delay)

    result = StageResult(
        schema_version=SCHEMA_VERSION,
        name=name,
        category=category,
        criticality=criticality,
        description=description,
        remediation=remediation,
        status="success" if code == 0 else "failed",
        exit_code=code,
        started_at=started_at,
        completed_at=now(),
        duration_seconds=round(time.monotonic() - started, 3),
        command=[redact(str(argument), secrets) for argument in command],
        attempts=attempts,
        failure_class=failure,
        error=error,
    )
    write_result(report_dir, result)
    return result


def evaluate_readiness(
    report_dir: Path,
    required_stages: Iterable[str],
    required_files: Iterable[Path],
    output: Path,
) -> Dict[str, Any]:
    """Evaluate canonical publication readiness from explicit evidence only."""

    blockers: List[str] = []
    stage_states: Dict[str, str] = {}
    invalid_stage_reports: Dict[str, str] = {}
    for stage in required_stages:
        path = report_dir / f"{safe_name(stage)}.json"
        payload: object = None
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = None
        if payload is None:
            status = "missing"
        else:
            valid, detail = validate_stage_report(payload, stage)
            if valid:
                status = detail
            else:
                status = "invalid"
                invalid_stage_reports[stage] = detail
        stage_states[stage] = status
        if status != "success":
            blockers.append(f"stage:{stage}:{status}")

    file_states: Dict[str, str] = {}
    for path in required_files:
        state = "present" if path.is_file() and path.stat().st_size > 0 else "missing"
        file_states[str(path)] = state
        if state != "present":
            blockers.append(f"file:{path}:{state}")

    result: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "evaluated_at": now(),
        "publish_ready": not blockers,
        "status": "ready" if not blockers else "degraded",
        "blockers": blockers,
        "required_stages": stage_states,
        "required_files": file_states,
        "invalid_stage_reports": invalid_stage_reports,
    }
    atomic_json(output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def context(output: Path) -> None:
    """Capture a small, non-sensitive execution context document."""

    atomic_json(
        output,
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "repository": os.getenv("GITHUB_REPOSITORY"),
            "workflow": os.getenv("GITHUB_WORKFLOW"),
            "run_id": os.getenv("GITHUB_RUN_ID"),
            "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
            "sha": os.getenv("GITHUB_SHA"),
            "ref": os.getenv("GITHUB_REF"),
        },
    )


def summary(report_dir: Path, output: Path) -> None:
    """Aggregate all stage JSON files into a deterministic summary."""

    stages: List[Dict[str, Any]] = []
    for path in sorted(report_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and "name" in payload:
            stages.append(payload)
    atomic_json(
        output,
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now(),
            "stages": stages,
        },
    )


def _add_common_metadata_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--category", default="general")
    parser.add_argument("--criticality", default="required")
    parser.add_argument("--description", default="")
    parser.add_argument("--remediation", default="")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--name", required=True)
    run_parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    run_parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    run_parser.add_argument("--retries", type=int, default=0)
    run_parser.add_argument("--retry-backoff", type=float, default=5.0)
    _add_common_metadata_arguments(run_parser)
    run_parser.add_argument("command", nargs=argparse.REMAINDER)

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--name", required=True)
    record_parser.add_argument("--status", required=True)
    record_parser.add_argument("--exit-code", type=int, default=0)
    record_parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    _add_common_metadata_arguments(record_parser)

    context_parser = subparsers.add_parser("context")
    context_parser.add_argument("--output", type=Path, default=DEFAULT_CONTEXT_OUTPUT)

    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    summary_parser.add_argument("--output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)

    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    evaluate_parser.add_argument("--required-stage", action="append", default=[])
    evaluate_parser.add_argument(
        "--required-file", type=Path, action="append", default=[]
    )
    evaluate_parser.add_argument(
        "--output", type=Path, default=DEFAULT_READINESS_OUTPUT
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Execute the requested evidence command."""

    args = build_parser().parse_args(argv)
    if args.cmd == "run":
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        run_stage(
            args.name,
            command,
            args.report_dir,
            category=args.category,
            criticality=args.criticality,
            description=args.description,
            remediation=args.remediation,
            timeout=args.timeout,
            retries=args.retries,
            retry_backoff=args.retry_backoff,
        )
    elif args.cmd == "record":
        record_stage(
            args.name,
            args.status,
            args.report_dir,
            category=args.category,
            criticality=args.criticality,
            description=args.description,
            remediation=args.remediation,
            exit_code=args.exit_code,
        )
    elif args.cmd == "context":
        context(args.output)
    elif args.cmd == "summary":
        summary(args.report_dir, args.output)
    else:
        evaluate_readiness(
            args.report_dir, args.required_stage, args.required_file, args.output
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
