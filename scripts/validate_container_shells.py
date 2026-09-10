# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate Bash-only commands in GitHub Actions job containers."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_workflows import _container_bash_shell_errors


def validate_workflow(data: dict[Any, Any]) -> list[str]:
    """Return violations using the repository's single shell-contract implementation."""
    return _container_bash_shell_errors(data)


def main() -> int:
    errors: list[str] = []
    for path in sorted(WORKFLOW_DIR.glob("*.y*ml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{path}: cannot parse workflow: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: workflow root must be a mapping")
            continue
        errors.extend(f"{path}: {error}" for error in validate_workflow(data))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: job-container shell contracts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
