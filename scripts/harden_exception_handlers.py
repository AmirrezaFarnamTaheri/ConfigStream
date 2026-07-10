# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add explicit diagnostics to audited broad exception handlers."""

from __future__ import annotations

import argparse
import ast
import difflib
import io
import json
import re
import tokenize
from collections import defaultdict
from pathlib import Path
from typing import Any


LOG_TEMPLATE = (
    'logging.getLogger(__name__).debug('
    '"Suppressed broad exception in {path}:{line}", exc_info=True)'
)


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for match in re.finditer("\n", source):
        offsets.append(match.end())
    return offsets


def _offset(offsets: list[int], line: int, column: int) -> int:
    return offsets[line - 1] + column


def _find_handler(tree: ast.AST, line: int) -> ast.ExceptHandler:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and node.lineno == line
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one exception handler at line {line}, found {len(matches)}"
        )
    return matches[0]


def _find_colon(source: str, handler: ast.ExceptHandler) -> tuple[int, int]:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    started = False
    depth = 0
    for token in tokens:
        if not started:
            if token.type == tokenize.NAME and token.string == "except" and token.start == (
                handler.lineno,
                handler.col_offset,
            ):
                started = True
            continue
        if token.type == tokenize.OP:
            if token.string in "([{":
                depth += 1
            elif token.string in ")]}":
                depth -= 1
            elif token.string == ":" and depth == 0:
                return token.start
    raise ValueError(f"Unable to locate except colon at line {handler.lineno}")


def _has_logging_import(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Import) and any(
            alias.name == "logging" for alias in node.names
        ):
            return True
    return False


def _import_insertion_offset(source: str, tree: ast.Module, offsets: list[int]) -> int:
    del source
    line = 0
    body = tree.body
    index = 0
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        line = body[0].end_lineno or body[0].lineno
        index = 1
    while index < len(body):
        node = body[index]
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            line = node.end_lineno or node.lineno
            index += 1
            continue
        break
    return offsets[line]


def _normalize_header(header: str) -> str:
    normalized = re.sub(r"\bBaseException\b", "Exception", header)
    if re.fullmatch(r"except\s*", normalized):
        normalized = normalized.rstrip() + " Exception"
    return normalized


def transform_source(source: str, path: str, target_lines: set[int]) -> str:
    tree = ast.parse(source, filename=path)
    offsets = _line_offsets(source)
    edits: list[tuple[int, int, str]] = []

    for line in sorted(target_lines):
        handler = _find_handler(tree, line)
        if not handler.body:
            raise ValueError(f"Exception handler at {path}:{line} has no body")
        colon_line, colon_col = _find_colon(source, handler)
        start = _offset(offsets, handler.lineno, handler.col_offset)
        colon = _offset(offsets, colon_line, colon_col)
        header = source[start:colon]
        normalized_header = _normalize_header(header)
        if normalized_header != header:
            edits.append((start, colon, normalized_header))

        first = handler.body[0]
        log_line = LOG_TEMPLATE.format(path=path, line=line)
        if first.lineno > colon_line:
            insertion = offsets[first.lineno - 1]
            indent = " " * first.col_offset
            edits.append((insertion, insertion, indent + log_line + "\n"))
        else:
            line_end = source.find("\n", colon)
            if line_end < 0:
                line_end = len(source)
            body_text = source[colon + 1 : line_end].lstrip()
            indent = " " * (handler.col_offset + 4)
            replacement = "\n" + indent + log_line
            if body_text:
                replacement += "\n" + indent + body_text
            edits.append((colon + 1, line_end, replacement))

    if target_lines and not _has_logging_import(tree):
        insertion = _import_insertion_offset(source, tree, offsets)
        prefix = "" if insertion == 0 else "\n"
        edits.append((insertion, insertion, prefix + "import logging\n"))

    for start, end, replacement in sorted(
        edits,
        key=lambda item: (item[0], item[1]),
        reverse=True,
    ):
        source = source[:start] + replacement + source[end:]
    ast.parse(source, filename=path)
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--patch-file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    report: dict[str, Any] = json.loads(args.report.read_text(encoding="utf-8"))
    targets: dict[str, set[int]] = defaultdict(set)
    for finding in report.get("findings", []):
        if finding.get("silent"):
            targets[str(finding["path"])].add(int(finding["line"]))

    patch_parts: list[str] = []
    changed_files = 0
    for path_text, lines in sorted(targets.items()):
        path = Path(path_text)
        original = path.read_text(encoding="utf-8")
        updated = transform_source(original, path_text, lines)
        if updated == original:
            continue
        changed_files += 1
        patch_parts.extend(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=f"a/{path_text}",
                tofile=f"b/{path_text}",
            )
        )
        if args.apply:
            path.write_text(updated, encoding="utf-8")

    patch = "".join(patch_parts)
    if args.patch_file:
        args.patch_file.write_text(patch, encoding="utf-8")
    print(f"Prepared diagnostics for {changed_files} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
