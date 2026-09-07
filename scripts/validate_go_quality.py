# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that native Go modules have unit, race, fuzz, and benchmark gates."""

from __future__ import annotations

import shlex
from pathlib import Path


def _go_test_commands(workflow: str) -> list[list[str]]:
    """Return tokenized ``go test`` shell commands from workflow run blocks."""

    commands: list[list[str]] = []
    for raw_line in workflow.splitlines():
        line = raw_line.strip()
        if not line.startswith("go test "):
            continue
        try:
            tokens = shlex.split(line)
        except ValueError:
            continue
        if tokens[:2] == ["go", "test"]:
            commands.append(tokens[2:])
    return commands


def _has_gate(
    commands: list[list[str]],
    *,
    required: tuple[str, ...],
    forbidden_prefixes: tuple[str, ...] = (),
) -> bool:
    for args in commands:
        if not all(token in args for token in required):
            continue
        if any(arg.startswith(prefix) for prefix in forbidden_prefixes for arg in args):
            continue
        return True
    return False


def validate(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    required_files = (
        "src/go/tester/main_test.go",
        "src/go/tester/scanner/scanner_test.go",
        "src/go/utls_client/main_test.go",
    )
    for relative in required_files:
        if not (root / relative).is_file():
            errors.append(f"missing native test file: {relative}")
    combined = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in required_files
        if (root / path).is_file()
    )
    for token in (
        "FuzzParseConfig",
        "FuzzParseTarget",
        "BenchmarkParseConfig",
        "BenchmarkParseTarget",
    ):
        if token not in combined:
            errors.append(f"missing Go fuzz/benchmark target: {token}")

    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    commands = _go_test_commands(workflow)
    gates = (
        (
            "go test ./...",
            _has_gate(
                commands,
                required=("./...",),
                forbidden_prefixes=("-race", "-fuzz=", "-bench="),
            ),
        ),
        (
            "go test -race ./...",
            _has_gate(commands, required=("-race", "./...")),
        ),
        (
            "-fuzz=FuzzParseConfig",
            _has_gate(commands, required=("-fuzz=FuzzParseConfig",)),
        ),
        (
            "-fuzz=FuzzParseTarget",
            _has_gate(commands, required=("-fuzz=FuzzParseTarget",)),
        ),
        ("-bench=.", _has_gate(commands, required=("-bench=.",))),
    )
    for label, present in gates:
        if not present:
            errors.append(f"CI missing Go quality command: {label}")
    return errors


def main() -> int:
    errors = validate(Path("."))
    if errors:
        print("ERROR: Go quality validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: Go unit, race, fuzz, and benchmark gates are declared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
