#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inventory and ratchet broad exception boundaries in production code."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BUDGET = ROOT / "config" / "exception-boundary-budget.json"
SCAN_ROOTS = (ROOT / "src" / "configstream", ROOT / "scripts")


def count_boundaries() -> dict[str, int]:
    counts: dict[str, int] = {}
    for scan_root in SCAN_ROOTS:
        for path in sorted(scan_root.rglob("*.py")):
            relative = path.relative_to(ROOT).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            count = 0
            for node in ast.walk(tree):
                if not isinstance(node, ast.Try):
                    continue
                for handler in node.handlers:
                    if handler.type is None:
                        count += 1
                    elif isinstance(handler.type, ast.Name) and handler.type.id in {
                        "Exception",
                        "BaseException",
                    }:
                        count += 1
            if count:
                counts[relative] = count
    return counts


def build_budget() -> dict[str, object]:
    counts = count_boundaries()
    return {
        "schema_version": 1,
        "policy": {
            "scope": ["src/configstream/**/*.py", "scripts/**/*.py"],
            "rule": "exact ratchet: new boundaries and stale ceilings fail CI",
            "target_total": 0,
            "required_boundary_behavior": "catch only at a recovery or translation boundary; preserve cancellation and fail closed for security/publication",
        },
        "total_ceiling": sum(counts.values()),
        "path_ceilings": counts,
    }


def validate() -> list[str]:
    if not BUDGET.exists():
        return [f"missing exception boundary budget: {BUDGET}"]
    try:
        budget = json.loads(BUDGET.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read exception boundary budget: {exc}"]
    actual = count_boundaries()
    expected = budget.get("path_ceilings")
    if not isinstance(expected, dict):
        return ["exception boundary budget missing path_ceilings"]
    normalized = {str(path): int(count) for path, count in expected.items()}
    errors: list[str] = []
    for path in sorted(set(actual) | set(normalized)):
        observed = actual.get(path, 0)
        ceiling = normalized.get(path)
        if ceiling is None:
            errors.append(
                f"unreviewed broad exception boundary path: {path} ({observed})"
            )
        elif observed > ceiling:
            errors.append(
                f"broad exception budget increased: {path}: {observed} > {ceiling}"
            )
        elif observed < ceiling:
            errors.append(
                f"stale broad exception ceiling must be ratcheted down: {path}: {observed} < {ceiling}"
            )
    total = sum(actual.values())
    ceiling_total = int(budget.get("total_ceiling", -1))
    if total != ceiling_total:
        errors.append(
            f"total broad exception budget is stale: actual={total}, ceiling={ceiling_total}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        BUDGET.parent.mkdir(parents=True, exist_ok=True)
        BUDGET.write_text(
            json.dumps(build_budget(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {BUDGET.relative_to(ROOT)}")
        return 0
    errors = validate()
    if errors:
        print("ERROR: exception boundary budget failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(
        f"OK: exception boundary budget exact ({sum(count_boundaries().values())} boundaries)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
