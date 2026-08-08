# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prevent oversized Python functions from growing or multiplying."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import TypedDict

THRESHOLD = 300
BUDGET_PATH = Path("config/function-size-budget.json")


class FunctionSizeBudget(TypedDict):
    schema_version: int
    threshold_lines: int
    policy: str
    target_oversized_function_count: int
    functions: dict[str, int]


def scan(root: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for base in (root / "src/configstream", root / "scripts"):
        for path in sorted(base.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                end = getattr(node, "end_lineno", None)
                if end is None:
                    continue
                size = end - node.lineno + 1
                if size >= THRESHOLD:
                    key = f"{path.relative_to(root).as_posix()}::{node.name}"
                    result[key] = size
    return dict(sorted(result.items()))


def generate(root: Path) -> FunctionSizeBudget:
    functions = scan(root)
    return {
        "schema_version": 1,
        "threshold_lines": THRESHOLD,
        "policy": "No new oversized functions; existing entries may only shrink until removed.",
        "target_oversized_function_count": 0,
        "functions": functions,
    }


def validate(root: Path) -> list[str]:
    root = Path(root)
    current = scan(root)
    path = root / BUDGET_PATH
    try:
        budget = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read function-size budget: {exc}"]
    expected = budget.get("functions", {})
    errors: list[str] = []
    for key, size in current.items():
        limit = expected.get(key)
        if limit is None:
            errors.append(f"new oversized function: {key} ({size} lines)")
        elif size > int(limit):
            errors.append(f"oversized function grew: {key} {limit} -> {size} lines")
    for key, limit in expected.items():
        if key not in current:
            errors.append(
                f"function-size budget is stale; remove improved/deleted entry: {key} ({limit} lines)"
            )
        elif current[key] < int(limit):
            errors.append(
                f"function-size budget is stale; lower {key} from {limit} to {current[key]}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(".")
    if args.write:
        payload = generate(root)
        path = root / BUDGET_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            f"OK: wrote function-size budget for {len(payload['functions'])} oversized functions"
        )
        return 0
    errors = validate(root)
    if errors:
        print("ERROR: function-size budget regressed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: no oversized Python function grew or appeared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
