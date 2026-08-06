# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate the machine-readable release state and generated STATUS.md."""

from __future__ import annotations

import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.release_state import (
    ALLOWED_GATE_STATUSES,
    ALLOWED_RELEASE_GATES,
    ALLOWED_VERDICTS,
    load_release_state,
    parse_timestamp,
    render_status,
)

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "STATUS.md"
READINESS_PATH = ROOT / "docs" / "readiness.json"
PYPROJECT_PATH = ROOT / "pyproject.toml"


def _project_metadata() -> tuple[str, list[str]]:
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise TypeError("pyproject.toml missing [project] table")
    version = project.get("version")
    classifiers = project.get("classifiers", [])
    if not isinstance(version, str) or not version:
        raise TypeError("pyproject.toml project.version must be a non-empty string")
    if not isinstance(classifiers, list) or not all(isinstance(v, str) for v in classifiers):
        raise TypeError("pyproject.toml project.classifiers must be a string list")
    return version, classifiers


def validate_status(*, now: str | None = None) -> list[str]:
    errors: list[str] = []
    try:
        state = load_release_state(READINESS_PATH)
    except (OSError, ValueError, TypeError) as exc:
        return [f"docs/readiness.json is invalid: {exc}"]

    try:
        project_version, classifiers = _project_metadata()
    except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError) as exc:
        return [f"pyproject.toml metadata is invalid: {exc}"]

    required_fields = {
        "schema_version",
        "project_version",
        "evaluated_at",
        "verdict",
        "release_gate",
        "production_ready",
        "required_gates",
        "release_invariant",
        "evidence_boundary",
    }
    for field in sorted(required_fields - state.keys()):
        errors.append(f"docs/readiness.json missing required field: {field}")

    if state.get("schema_version") != "2":
        errors.append("docs/readiness.json schema_version must be '2'")
    if state.get("project_version") != project_version:
        errors.append(
            "docs/readiness.json project_version does not match pyproject.toml: "
            f"{state.get('project_version')!r} != {project_version!r}"
        )

    verdict = state.get("verdict")
    release_gate = state.get("release_gate")
    production_ready = state.get("production_ready")
    if verdict not in ALLOWED_VERDICTS:
        errors.append(f"docs/readiness.json verdict must be one of {sorted(ALLOWED_VERDICTS)}")
    if release_gate not in ALLOWED_RELEASE_GATES:
        errors.append(
            f"docs/readiness.json release_gate must be one of {sorted(ALLOWED_RELEASE_GATES)}"
        )
    if not isinstance(production_ready, bool):
        errors.append("docs/readiness.json production_ready must be a boolean")

    gates = state.get("required_gates")
    all_gates_passing = False
    if not isinstance(gates, dict) or not gates:
        errors.append("docs/readiness.json required_gates must be a non-empty object")
    else:
        all_gates_passing = True
        for name, gate in sorted(gates.items()):
            if not isinstance(gate, dict):
                errors.append(f"required gate {name!r} must be an object")
                all_gates_passing = False
                continue
            status = gate.get("status")
            evidence = gate.get("evidence")
            if status not in ALLOWED_GATE_STATUSES:
                errors.append(
                    f"required gate {name!r} status must be one of {sorted(ALLOWED_GATE_STATUSES)}"
                )
            if status != "passing":
                all_gates_passing = False
            if not isinstance(evidence, list) or not all(
                isinstance(item, str) and item for item in evidence
            ):
                errors.append(f"required gate {name!r} evidence must be a string list")
            if status == "passing" and not evidence:
                errors.append(f"required gate {name!r} cannot pass without evidence")

    is_pass = verdict == "PASS" and release_gate == "ready" and production_ready is True
    if is_pass and not all_gates_passing:
        errors.append("PASS/ready/production_ready requires all required gates to be passing")
    if production_ready is True and not is_pass:
        errors.append("production_ready may be true only for a PASS verdict with release_gate=ready")
    if all_gates_passing and not is_pass:
        errors.append("all required gates pass but the release state is not PASS/ready")

    stable_classifier = "Development Status :: 5 - Production/Stable"
    beta_classifier = "Development Status :: 4 - Beta"
    if is_pass:
        if stable_classifier not in classifiers:
            errors.append("PASS releases require the Production/Stable classifier")
    else:
        if stable_classifier in classifiers:
            errors.append("non-PASS releases must not use the Production/Stable classifier")
        if beta_classifier not in classifiers:
            errors.append("non-PASS releases require the Beta classifier")

    evaluated_at = state.get("evaluated_at")
    if isinstance(evaluated_at, str):
        try:
            evaluated = parse_timestamp(evaluated_at)
            reference = parse_timestamp(now) if now else datetime.now(timezone.utc)
            if evaluated > reference + timedelta(minutes=5):
                errors.append("docs/readiness.json evaluated_at is in the future")
        except ValueError as exc:
            errors.append(f"docs/readiness.json evaluated_at is invalid: {exc}")
    else:
        errors.append("docs/readiness.json evaluated_at must be a timestamp string")

    try:
        actual_status = STATUS_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"STATUS.md could not be read: {exc}")
    else:
        expected_status = render_status(state)
        if actual_status != expected_status:
            errors.append(
                "STATUS.md does not match docs/readiness.json; regenerate with scripts/generate_status.py"
            )

    return errors


def main() -> None:
    errors = validate_status()
    if errors:
        print("ERROR: release status validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: machine-readable release state and generated STATUS.md are consistent.")


if __name__ == "__main__":
    main()
