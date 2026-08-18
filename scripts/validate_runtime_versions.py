# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate runtime/toolchain declarations against one canonical manifest."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _expect(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate_repository(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    try:
        versions = _load_json(root / "config/runtime-versions.json")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"runtime manifest unreadable: {type(exc).__name__}: {exc}"]

    try:
        python = versions["python"]
        node = versions["node"]
        go = versions["go"]
        python_min = str(python["minimum"])
        python_container = str(python["container"])
        node_min = int(node["minimum_major"])
        node_container = str(node["container"])
        go_language = str(go["language"])
        go_toolchain = str(go["toolchain"])
        go_ci = str(go.get("ci", go_toolchain))
        go_container = str(go["container"])
    except (KeyError, TypeError, ValueError) as exc:
        return [f"runtime manifest schema invalid: {type(exc).__name__}: {exc}"]

    try:
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        requires_python = str(pyproject["project"]["requires-python"])
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        errors.append(f"pyproject runtime declaration unreadable: {type(exc).__name__}")
    else:
        _expect(
            errors,
            requires_python == f">={python_min}",
            f"pyproject requires-python {requires_python!r} != '>={python_min}'",
        )

    try:
        package = _load_json(root / "package.json")
        node_engine = str(package.get("engines", {}).get("node", ""))
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
        AttributeError,
    ) as exc:
        errors.append(
            f"package.json runtime declaration unreadable: {type(exc).__name__}"
        )
    else:
        _expect(
            errors,
            node_engine == f">={node_min}",
            f"package.json engines.node {node_engine!r} != '>={node_min}'",
        )

    try:
        go_mod = (root / "src/go/tester/go.mod").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"go.mod unreadable: {type(exc).__name__}")
    else:
        language_match = re.search(r"(?m)^go\s+(\S+)\s*$", go_mod)
        toolchain_match = re.search(r"(?m)^toolchain\s+go(\S+)\s*$", go_mod)
        _expect(
            errors,
            bool(language_match and language_match.group(1) == go_language),
            f"go.mod language version must be {go_language}",
        )
        _expect(
            errors,
            bool(toolchain_match and toolchain_match.group(1) == go_toolchain),
            f"go.mod toolchain must be go{go_toolchain}",
        )

    try:
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Dockerfile unreadable: {type(exc).__name__}")
    else:
        for required in (
            f"FROM golang:{go_container}-alpine@sha256:",
            f"FROM node:{node_container}-slim@sha256:",
            f"FROM python:{python_container}-slim@sha256:",
        ):
            _expect(
                errors,
                required in dockerfile,
                f"Dockerfile missing canonical base: {required}",
            )

    workflow_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((root / ".github/workflows").glob("*.y*ml"))
    )
    _expect(
        errors,
        f"go-version: '{go_ci}'" in workflow_text
        or f'go-version: "{go_ci}"' in workflow_text,
        f"workflows must use exact Go {go_ci}",
    )
    for match in re.finditer(r"node-version:\s*['\"]?([^'\"\s]+)", workflow_text):
        _expect(
            errors,
            match.group(1) == str(node["ci"]),
            f"workflow node-version {match.group(1)!r} != {node['ci']!r}",
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    errors = validate_repository(args.root)
    if errors:
        print("ERROR: runtime version drift detected")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: runtime versions match config/runtime-versions.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
