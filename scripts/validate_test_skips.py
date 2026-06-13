# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that pytest skips are narrow, explained, and environment-bound."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOTS = ("tests",)
SOURCE_SUFFIXES = {".py"}

ENVIRONMENT_REASON_RE = re.compile(
    r"\b("
    r"browser|browsers|chromium|containerized|dependency|directory|environment|"
    r"fixture|frontend|generator|installed|loopback|network|node|playwright|"
    r"platform|required|sample|server|tool|unavailable|unsupported"
    r")\b",
    re.IGNORECASE,
)
DISALLOWED_REASON_RE = re.compile(
    r"\b(todo|fixme|later|temporary|temporarily|disabled|investigate|wip)\b",
    re.IGNORECASE,
)
MIN_REASON_LENGTH = 12


@dataclass(frozen=True)
class PytestAliases:
    pytest_modules: frozenset[str]
    mark_modules: frozenset[str]
    skip_functions: frozenset[str]


def _iter_source_files(scan_roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for rel_root in scan_roots:
        root = ROOT / rel_root
        if root.is_file() and root.suffix in SOURCE_SUFFIXES:
            files.append(root)
            continue
        if not root.exists():
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix in SOURCE_SUFFIXES
        )
    return sorted(files)


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
    return None


def _collect_pytest_aliases(tree: ast.AST) -> PytestAliases:
    pytest_modules = {"pytest"}
    mark_modules: set[str] = set()
    skip_functions: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pytest":
                    pytest_modules.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "pytest":
            for alias in node.names:
                bound_name = alias.asname or alias.name
                if alias.name == "mark":
                    mark_modules.add(bound_name)
                elif alias.name == "skip":
                    skip_functions.add(bound_name)

    return PytestAliases(
        pytest_modules=frozenset(pytest_modules),
        mark_modules=frozenset(mark_modules),
        skip_functions=frozenset(skip_functions),
    )


def _skip_kind(name: str | None, aliases: PytestAliases) -> str | None:
    if not name:
        return None
    if name in aliases.skip_functions:
        return "pytest.skip"
    for pytest_name in aliases.pytest_modules:
        if name == f"{pytest_name}.skip":
            return "pytest.skip"
        if name == f"{pytest_name}.mark.skip":
            return "pytest.mark.skip"
        if name == f"{pytest_name}.mark.skipif":
            return "pytest.mark.skipif"
    for mark_name in aliases.mark_modules:
        if name == f"{mark_name}.skip":
            return "pytest.mark.skip"
        if name == f"{mark_name}.skipif":
            return "pytest.mark.skipif"
    return None


def _string_constant(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _reason_from_call(kind: str, node: ast.Call) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == "reason":
            return _string_constant(keyword.value)

    if kind in {"pytest.skip", "pytest.mark.skip"} and node.args:
        return _string_constant(node.args[0])
    if kind == "pytest.mark.skipif" and len(node.args) >= 2:
        return _string_constant(node.args[1])
    return None


def _is_constant_skipif_condition(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, bool)


def _normalize_reason(reason: str) -> str:
    return " ".join(reason.split())


class _SkipVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str, aliases: PytestAliases) -> None:
        self.rel_path = rel_path
        self.aliases = aliases
        self.errors: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        kind = _skip_kind(_qualified_name(node.func), self.aliases)
        if kind == "pytest.mark.skip":
            self._add(
                node,
                "permanent pytest.mark.skip is forbidden; use skipif with an "
                "environment/tooling predicate or remove the dead test",
            )
        elif kind == "pytest.mark.skipif":
            self._validate_skipif(node)
        elif kind == "pytest.skip":
            self._validate_reason(kind, node, _reason_from_call(kind, node))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._validate_bare_decorators(node.decorator_list)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._validate_bare_decorators(node.decorator_list)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._validate_bare_decorators(node.decorator_list)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._validate_bare_marker(node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self._validate_bare_marker(node.value)
        self.generic_visit(node)

    def _validate_bare_decorators(self, decorators: list[ast.expr]) -> None:
        for decorator in decorators:
            if not isinstance(decorator, ast.Call):
                self._validate_bare_marker(decorator)

    def _validate_bare_marker(self, node: ast.AST) -> None:
        kind = _skip_kind(_qualified_name(node), self.aliases)
        if kind == "pytest.mark.skip":
            self._add(node, "bare pytest.mark.skip is forbidden")
        elif kind == "pytest.mark.skipif":
            self._add(
                node, "bare pytest.mark.skipif must include a predicate and reason"
            )

    def _validate_skipif(self, node: ast.Call) -> None:
        if not node.args:
            self._add(node, "pytest.mark.skipif must include a predicate")
            return
        if _is_constant_skipif_condition(node.args[0]):
            self._add(
                node,
                "pytest.mark.skipif must not use a constant predicate; gate it "
                "on a real environment/tooling condition",
            )
        self._validate_reason(
            "pytest.mark.skipif", node, _reason_from_call("pytest.mark.skipif", node)
        )

    def _validate_reason(
        self,
        kind: str,
        node: ast.AST,
        reason: str | None,
    ) -> None:
        if reason is None:
            self._add(node, f"{kind} must include a literal reason")
            return

        normalized = _normalize_reason(reason)
        if len(normalized) < MIN_REASON_LENGTH:
            self._add(node, f"{kind} reason is too short to be auditable")
        if DISALLOWED_REASON_RE.search(normalized):
            self._add(
                node,
                f"{kind} reason must not describe deferred or disabled work",
            )
        if not ENVIRONMENT_REASON_RE.search(normalized):
            self._add(
                node,
                f"{kind} reason must identify the missing environment, tooling, "
                "fixture, platform, or generated sample condition",
            )

    def _add(self, node: ast.AST, message: str) -> None:
        line = getattr(node, "lineno", 1)
        self.errors.append(f"{self.rel_path}:{line}: {message}")


def validate_test_skips(scan_roots: tuple[str, ...] = DEFAULT_SCAN_ROOTS) -> list[str]:
    errors: list[str] = []
    for path in _iter_source_files(scan_roots):
        rel_path = str(path.relative_to(ROOT))
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{rel_path}: cannot decode as UTF-8: {exc}")
            continue

        try:
            tree = ast.parse(source, filename=rel_path)
        except SyntaxError as exc:
            errors.append(f"{rel_path}: Python parse failed: {exc}")
            continue

        visitor = _SkipVisitor(rel_path, _collect_pytest_aliases(tree))
        visitor.visit(tree)
        errors.extend(visitor.errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional repository-relative test files or directories to scan.",
    )
    args = parser.parse_args(argv)

    scan_roots = tuple(args.paths) if args.paths else DEFAULT_SCAN_ROOTS
    errors = validate_test_skips(scan_roots)
    if errors:
        for error in errors:
            print(error)
        return 1

    print("OK: pytest skips are environment-bound and auditable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
