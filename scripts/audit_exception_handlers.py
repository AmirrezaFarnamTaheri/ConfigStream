# SPDX-License-Identifier: AGPL-3.0-or-later
"""Audit broad Python exception handlers and identify silent failure paths."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence


LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical", "log"}
OUTPUT_METHODS = {"echo", "secho", "print", "write", "print_exception"}
BROAD_NAMES = {"Exception", "BaseException"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    handler: str
    has_log: bool
    has_output: bool
    reraises: bool
    terminates: bool
    body_summary: str

    @property
    def silent(self) -> bool:
        return not self.has_log and not self.has_output and not self.reraises


def _handler_name(node: ast.ExceptHandler) -> str:
    if node.type is None:
        return "bare"
    if isinstance(node.type, ast.Name):
        return node.type.id
    if isinstance(node.type, ast.Tuple):
        names = [item.id for item in node.type.elts if isinstance(item, ast.Name)]
        return ",".join(names)
    return ast.unparse(node.type)


def _is_broad(node: ast.ExceptHandler) -> bool:
    if node.type is None:
        return True
    if isinstance(node.type, ast.Name):
        return node.type.id in BROAD_NAMES
    if isinstance(node.type, ast.Tuple):
        return any(
            isinstance(item, ast.Name) and item.id in BROAD_NAMES
            for item in node.type.elts
        )
    return False


def _root_name(expression: ast.expr) -> str | None:
    current: ast.expr = expression
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def _is_logging_call(call: ast.Call) -> bool:
    function = call.func
    if isinstance(function, ast.Attribute) and function.attr in LOG_METHODS:
        root = _root_name(function)
        if root in {"logger", "logging", "log"} or bool(
            root and root.endswith("logger")
        ):
            return True
        receiver = function.value
        if (
            isinstance(receiver, ast.Call)
            and isinstance(receiver.func, ast.Attribute)
            and receiver.func.attr == "getLogger"
            and _root_name(receiver.func) == "logging"
        ):
            return True
    if isinstance(function, ast.Attribute) and function.attr == "warn":
        return _root_name(function) == "warnings"
    return False


def _is_user_output_call(call: ast.Call) -> bool:
    function = call.func
    if isinstance(function, ast.Name):
        return function.id == "print"
    if isinstance(function, ast.Attribute) and function.attr in OUTPUT_METHODS:
        root = _root_name(function)
        return root in {
            "click",
            "typer",
            "console",
            "rich_console",
            "traceback",
            "sys",
        }
    return False


def _contains_call(
    node: ast.ExceptHandler,
    predicate: Callable[[ast.Call], bool],
) -> bool:
    return any(
        isinstance(child, ast.Call) and predicate(child)
        for child in ast.walk(node)
    )


def _contains_reraise(node: ast.ExceptHandler) -> bool:
    return any(isinstance(child, ast.Raise) for child in ast.walk(node))


def _terminates_control_flow(node: ast.ExceptHandler) -> bool:
    return any(
        isinstance(child, (ast.Return, ast.Break, ast.Continue))
        for child in ast.walk(node)
    )


def _body_summary(node: ast.ExceptHandler) -> str:
    statements = [type(statement).__name__ for statement in node.body[:5]]
    if len(node.body) > 5:
        statements.append("...")
    return ",".join(statements) or "empty"


def audit_file(path: Path, root: Path) -> list[Finding]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise RuntimeError(f"Unable to parse {path}: {type(exc).__name__}") from exc

    relative_path = path.resolve().relative_to(root.resolve()).as_posix()
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or not _is_broad(node):
            continue
        findings.append(
            Finding(
                path=relative_path,
                line=node.lineno,
                handler=_handler_name(node),
                has_log=_contains_call(node, _is_logging_call),
                has_output=_contains_call(node, _is_user_output_call),
                reraises=_contains_reraise(node),
                terminates=_terminates_control_flow(node),
                body_summary=_body_summary(node),
            )
        )
    return findings


def iter_python_files(paths: Sequence[Path]) -> Iterable[tuple[Path, Path]]:
    repository_root = Path.cwd()
    for root in paths:
        if root.is_file() and root.suffix == ".py":
            yield root, repository_root
            continue
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if any(
                part in {".venv", "venv", "build", "dist", "node_modules"}
                for part in path.parts
            ):
                continue
            yield path, repository_root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", default=["src/configstream", "scripts", "tools"])
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--fail-on-unlogged", action="store_true")
    args = parser.parse_args()

    findings: list[Finding] = []
    for path, root in iter_python_files([Path(item) for item in args.paths]):
        findings.extend(audit_file(path, root))

    findings.sort(key=lambda item: (item.path, item.line))
    silent = [finding for finding in findings if finding.silent]
    report = {
        "broad_handler_count": len(findings),
        "unlogged_broad_handler_count": len(silent),
        "findings": [
            {**asdict(finding), "silent": finding.silent}
            for finding in findings
        ],
    }

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(
        f"Broad handlers: {len(findings)}; unlogged broad handlers: {len(silent)}"
    )
    for finding in silent:
        print(
            f"{finding.path}:{finding.line}: {finding.handler} -> "
            f"{finding.body_summary}"
        )

    return 1 if args.fail_on_unlogged and silent else 0


if __name__ == "__main__":
    raise SystemExit(main())
