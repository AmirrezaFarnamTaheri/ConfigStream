# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run ConfigStream verification through one evidence-producing entry point."""

from __future__ import annotations

import argparse
import json
import importlib.util
import re
import os
import signal
import shutil
import subprocess  # nosec B404
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

MAX_CAPTURE_CHARS = 40_000


@dataclass(frozen=True)
class Stage:
    name: str
    command: tuple[str, ...]
    required_tool: str | None = None
    timeout_seconds: int = 120
    workdir: str = "."
    required_paths: tuple[str, ...] = ()
    required_python_modules: tuple[str, ...] = ()
    minimum_tool_version: tuple[int, ...] | None = None
    version_command: tuple[str, ...] = ()
    environment: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class StageResult:
    name: str
    command: tuple[str, ...]
    status: str
    exit_code: int | None
    duration_seconds: float
    output: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["command"] = list(self.command)
        return payload


def build_plan(profile: str) -> list[Stage]:
    python = sys.executable
    static = [
        Stage("versions", (python, "scripts/validate_versions.py")),
        Stage("changelog", (python, "scripts/validate_changelog.py")),
        Stage("action-pins", (python, "scripts/validate_action_pins.py")),
        Stage("workflows", (python, "scripts/validate_workflows.py")),
        Stage("runtime-versions", (python, "scripts/validate_runtime_versions.py")),
        Stage("container-pins", (python, "scripts/validate_container_pins.py")),
        Stage("dependency-drift", (python, "scripts/check_dependency_drift.py")),
        Stage("repository-hygiene", (python, "scripts/validate_repository_hygiene.py")),
        Stage(
            "instruction-consistency",
            (python, "scripts/validate_instruction_consistency.py"),
        ),
        Stage(
            "documentation-links", (python, "scripts/validate_documentation_links.py")
        ),
        Stage("maturity-tiers", (python, "scripts/validate_maturity_tiers.py")),
        Stage("go-quality-contract", (python, "scripts/validate_go_quality.py")),
        Stage("release-controls", (python, "scripts/validate_release_controls.py")),
        Stage(
            "environment-catalog",
            (python, "scripts/generate_environment_catalog.py", "--check"),
        ),
        Stage(
            "supply-chain-evidence",
            (python, "scripts/generate_supply_chain_evidence.py", "--check"),
        ),
        Stage(
            "dependency-inventory",
            (python, "scripts/generate_dependency_inventory.py", "--check"),
        ),
        Stage(
            "source-admission",
            (python, "scripts/generate_source_admission.py", "--check"),
        ),
        Stage("debt-matrix", (python, "scripts/generate_debt_matrix.py", "--check")),
        Stage(
            "triage-report", (python, "scripts/generate_triage_report.py", "--check")
        ),
        Stage(
            "capability-registry", (python, "scripts/validate_capability_registry.py")
        ),
        Stage("core-compatibility", (python, "scripts/validate_core_compatibility.py")),
        Stage("module-ownership", (python, "scripts/validate_module_ownership.py")),
        Stage("license-headers", (python, "scripts/check_license_headers.py")),
        Stage("test-skip-policy", (python, "scripts/validate_test_skips.py")),
        Stage("import-cycles", (python, "scripts/validate_import_cycles.py")),
        Stage(
            "function-size-budget", (python, "scripts/validate_function_size_budget.py")
        ),
        Stage(
            "exception-boundaries", (python, "scripts/validate_exception_boundaries.py")
        ),
        Stage(
            "repository-forensics",
            (python, "scripts/collect_repository_forensics.py", "--check"),
        ),
        Stage("status", (python, "scripts/validate_status.py")),
        Stage(
            "python-compile",
            (python, "-m", "compileall", "-q", "src", "scripts", "tests/unit"),
        ),
    ]
    release_tail = [
        Stage("assets", (python, "scripts/validate_assets.py")),
        Stage("claim-ledger", (python, "scripts/validate_claim_ledger.py")),
        Stage("protocol-matrix", (python, "scripts/validate_protocol_matrix.py")),
        Stage("output-matrix", (python, "scripts/validate_output_matrix.py")),
        Stage(
            "generated-output-docs",
            (python, "scripts/generate_output_docs.py", "--check"),
        ),
        Stage(
            "frontend-build",
            ("npm", "run", "build"),
            required_tool="npm",
            timeout_seconds=900,
            required_paths=("node_modules/.bin/vite",),
        ),
        Stage(
            "focused-regressions",
            (
                python,
                "-m",
                "pytest",
                "-q",
                "-p",
                "pytest_asyncio.plugin",
                "tests/unit/test_validate_status.py",
                "tests/unit/test_validate_action_pins.py",
                "tests/unit/test_deploy_artifact_smoke.py",
                "tests/unit/test_runtime_health.py",
                "tests/unit/test_validate_runtime_versions.py",
                "tests/unit/test_environment_catalog.py",
                "tests/unit/test_snapshot_pages_release.py",
                "tests/unit/test_source_admission.py",
                "tests/unit/test_backpressure_policy.py",
                "tests/unit/test_cache_compaction.py",
                "tests/unit/security/test_transport.py",
                "tests/unit/test_fetcher_pinned_request.py",
            ),
            timeout_seconds=900,
            environment=(("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1"),),
        ),
    ]
    release = static + release_tail
    full = release + [
        Stage(
            "python-unit",
            (python, "scripts/run_test_profile.py", "unit"),
            timeout_seconds=3600,
            required_python_modules=("aiohttp_socks", "slowapi", "geoip2"),
        ),
        Stage(
            "python-integration",
            (python, "scripts/run_test_profile.py", "integration"),
            timeout_seconds=3600,
            required_python_modules=("aiohttp_socks", "slowapi", "geoip2"),
        ),
        Stage(
            "frontend-browser",
            (python, "scripts/run_test_profile.py", "frontend-browser"),
            required_tool="npm",
            timeout_seconds=180,
            required_paths=("node_modules/.bin/playwright",),
        ),
        Stage(
            "go-tester-unit",
            ("go", "test", "./..."),
            required_tool="go",
            timeout_seconds=3600,
            workdir="src/go/tester",
            minimum_tool_version=(1, 24, 0),
            version_command=("go", "version"),
        ),
        Stage(
            "go-tester-race",
            ("go", "test", "-race", "./..."),
            required_tool="go",
            timeout_seconds=3600,
            workdir="src/go/tester",
            minimum_tool_version=(1, 24, 0),
            version_command=("go", "version"),
        ),
        Stage(
            "go-tester-fuzz",
            ("go", "test", "-run=^$", "-fuzz=FuzzParseConfig", "-fuzztime=5s", "."),
            required_tool="go",
            timeout_seconds=600,
            workdir="src/go/tester",
            minimum_tool_version=(1, 24, 0),
            version_command=("go", "version"),
        ),
        Stage(
            "go-tester-benchmark",
            ("go", "test", "-run=^$", "-bench=.", "-benchtime=100ms", "./..."),
            required_tool="go",
            timeout_seconds=900,
            workdir="src/go/tester",
            minimum_tool_version=(1, 24, 0),
            version_command=("go", "version"),
        ),
        Stage(
            "go-utls-unit",
            ("go", "test", "./..."),
            required_tool="go",
            timeout_seconds=1800,
            workdir="src/go/utls_client",
            minimum_tool_version=(1, 24, 3),
            version_command=("go", "version"),
        ),
        Stage(
            "go-utls-race",
            ("go", "test", "-race", "./..."),
            required_tool="go",
            timeout_seconds=1800,
            workdir="src/go/utls_client",
            minimum_tool_version=(1, 24, 3),
            version_command=("go", "version"),
        ),
        Stage(
            "go-utls-fuzz",
            ("go", "test", "-run=^$", "-fuzz=FuzzParseTarget", "-fuzztime=5s", "."),
            required_tool="go",
            timeout_seconds=600,
            workdir="src/go/utls_client",
            minimum_tool_version=(1, 24, 3),
            version_command=("go", "version"),
        ),
        Stage(
            "go-utls-benchmark",
            ("go", "test", "-run=^$", "-bench=.", "-benchtime=100ms", "./..."),
            required_tool="go",
            timeout_seconds=900,
            workdir="src/go/utls_client",
            minimum_tool_version=(1, 24, 3),
            version_command=("go", "version"),
        ),
        Stage(
            "rust-test",
            ("cargo", "test", "--locked"),
            required_tool="cargo",
            timeout_seconds=1800,
            workdir="src/rust/ss_checker",
        ),
    ]
    extended = full[len(release) :]
    plans = {
        "static": static,
        "release-tail": release_tail,
        "release": release,
        "extended": extended,
        "full": full,
    }
    if profile not in plans:
        raise ValueError(f"unknown verification profile: {profile}")
    return plans[profile]


def _run_process(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: float,
) -> tuple[int | None, str, bool]:
    """Run one bounded child and terminate its whole process group on timeout."""
    process = subprocess.Popen(  # nosec B603
        list(command),
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=os.name == "posix",
    )
    try:
        output, _ = process.communicate(timeout=timeout_seconds)
        return int(process.returncode), output or "", False
    except subprocess.TimeoutExpired as exc:
        if os.name == "posix" and hasattr(os, "killpg") and hasattr(signal, "SIGKILL"):
            try:
                os.killpg(process.pid, signal.SIGKILL)  # type: ignore[attr-defined]
            except ProcessLookupError:
                pass
        else:
            process.kill()
        trailing, _ = process.communicate()
        captured = exc.output or ""
        if isinstance(captured, bytes):
            captured = captured.decode(errors="replace")
        return None, str(captured) + (trailing or ""), True


def _run_stage(root: Path, stage: Stage, env: dict[str, str]) -> StageResult:
    tool = stage.required_tool or stage.command[0]
    missing_paths = [
        path
        for path in stage.required_paths
        if not (root / stage.workdir / path).exists()
    ]
    missing_modules = [
        module
        for module in stage.required_python_modules
        if importlib.util.find_spec(module) is None
    ]
    if missing_modules:
        return StageResult(
            name=stage.name,
            command=stage.command,
            status="unavailable",
            exit_code=None,
            duration_seconds=0.0,
            output="required Python modules not installed: "
            + ", ".join(missing_modules),
        )
    if missing_paths:
        return StageResult(
            name=stage.name,
            command=stage.command,
            status="unavailable",
            exit_code=None,
            duration_seconds=0.0,
            output="required project artifact not found: " + ", ".join(missing_paths),
        )
    if not (Path(tool).is_file() or shutil.which(tool)):
        return StageResult(
            name=stage.name,
            command=stage.command,
            status="unavailable",
            exit_code=None,
            duration_seconds=0.0,
            output=f"required tool not found: {tool}",
        )
    if stage.minimum_tool_version and stage.version_command:
        version_code, version_output, version_timed_out = _run_process(
            stage.version_command,
            cwd=root / stage.workdir,
            env=env,
            timeout_seconds=15,
        )
        if version_timed_out or version_code != 0:
            return StageResult(
                stage.name,
                stage.command,
                "unavailable",
                version_code,
                0.0,
                "could not run required tool version command",
            )
        match = re.search(
            r"(?:go|node |v)(\d+)\.(\d+)(?:\.(\d+))?", version_output or ""
        )
        if not match:
            return StageResult(
                stage.name,
                stage.command,
                "unavailable",
                None,
                0.0,
                "could not determine required tool version",
            )
        observed = tuple(int(value or 0) for value in match.groups())
        required = tuple(stage.minimum_tool_version) + (0,) * (
            3 - len(stage.minimum_tool_version)
        )
        if observed < required:
            return StageResult(
                stage.name,
                stage.command,
                "unavailable",
                None,
                0.0,
                f"tool version {observed} is below required {required}",
            )
    stage_env = env.copy()
    stage_env.update(dict(stage.environment))
    started = time.monotonic()
    exit_code, output, timed_out = _run_process(
        stage.command,
        cwd=root / stage.workdir,
        env=stage_env,
        timeout_seconds=stage.timeout_seconds,
    )
    if timed_out:
        status = "failed"
        output += "\nTIMEOUT"
    else:
        status = "success" if exit_code == 0 else "failed"
    duration = time.monotonic() - started
    if len(output) > MAX_CAPTURE_CHARS:
        output = "[output truncated]\n" + output[-MAX_CAPTURE_CHARS:]
    return StageResult(
        name=stage.name,
        command=stage.command,
        status=status,
        exit_code=exit_code,
        duration_seconds=round(duration, 3),
        output=output,
    )


def _build_stage_environment(root: Path) -> dict[str, str]:
    """Build a deterministic child environment without parent test instrumentation."""
    env = os.environ.copy()
    for key in tuple(env):
        if (
            key == "PYTEST_CURRENT_TEST"
            or key == "COVERAGE_PROCESS_START"
            or key.startswith("COV_CORE_")
            or key.startswith("DD_")
        ):
            env.pop(key, None)
    env.pop("PYTHONSTARTUP", None)
    env.pop("PYTHONINSPECT", None)
    env["PYTHONPATH"] = str(root / "src")
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONHASHSEED"] = "0"
    env.setdefault("ENVIRONMENT", "test")
    env.setdefault("GOTOOLCHAIN", "local")
    return env


def verify(
    root: Path,
    *,
    profile: str,
    report_path: Path,
    stop_on_failure: bool = True,
) -> bool:
    root = Path(root).resolve()
    report_path = Path(report_path)
    plan = build_plan(profile)
    env = _build_stage_environment(root)
    results: list[StageResult] = []
    for stage in plan:
        print(f"[{stage.name}] {' '.join(stage.command)}", flush=True)
        result = _run_stage(root, stage, env)
        results.append(result)
        print(f"[{stage.name}] {result.status}", flush=True)
        if stop_on_failure and result.status == "failed":
            break

    counts = {
        status: sum(result.status == status for result in results)
        for status in ("success", "failed", "unavailable")
    }
    omitted = len(plan) - len(results)
    payload = {
        "schema_version": 1,
        "profile": profile,
        "repository": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {**counts, "omitted_after_failure": omitted},
        "results": [result.to_dict() for result in results],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return counts["failed"] == 0 and counts["unavailable"] == 0 and omitted == 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--profile",
        choices=("static", "release-tail", "release", "extended", "full"),
        default="release",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("verification-evidence/repository-verification.json"),
    )
    parser.add_argument("--continue-on-failure", action="store_true")
    args = parser.parse_args(argv)
    ok = verify(
        args.root,
        profile=args.profile,
        report_path=args.report,
        stop_on_failure=not args.continue_on_failure,
    )
    print(f"Verification report: {args.report}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
