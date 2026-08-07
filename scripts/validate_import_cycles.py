#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fail when first-party Python modules contain import cycles."""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src" / "configstream"


def module_name(path: Path, source_parent: Path) -> str:
    relative = path.relative_to(source_parent).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def build_graph(source_root: Path) -> dict[str, set[str]]:
    source_root = Path(source_root)
    source_parent = source_root.parent
    paths = sorted(source_root.rglob("*.py"))
    names = {path: module_name(path, source_parent) for path in paths}
    known = set(names.values())
    graph: dict[str, set[str]] = {name: set() for name in known}

    for path, current in names.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        package = current.split(".") if path.name == "__init__.py" else current.split(".")[:-1]
        for node in ast.walk(tree):
            imports: list[str] = []
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    keep = max(0, len(package) - node.level + 1)
                    base = package[:keep]
                    module = ".".join(
                        base + ((node.module or "").split(".") if node.module else [])
                    )
                else:
                    module = node.module or ""
                if module:
                    imports.append(module)
                    imports.extend(
                        f"{module}.{alias.name}"
                        for alias in node.names
                        if alias.name != "*"
                    )
            for imported in imports:
                parts = imported.split(".")
                for index in range(len(parts), 0, -1):
                    candidate = ".".join(parts[:index])
                    if candidate in known:
                        if candidate != current:
                            graph[current].add(candidate)
                        break
    return graph


def strongly_connected_components(graph: dict[str, set[str]]) -> list[tuple[str, ...]]:
    index = 0
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for neighbour in graph.get(node, set()):
            if neighbour not in indexes:
                visit(neighbour)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbour])
            elif neighbour in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[neighbour])
        if lowlinks[node] != indexes[node]:
            return
        component: list[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1:
            components.append(tuple(sorted(component)))

    for node in sorted(graph):
        if node not in indexes:
            visit(node)
    return sorted(components)


def find_cycles(source_root: Path = SOURCE_ROOT) -> list[tuple[str, ...]]:
    return strongly_connected_components(build_graph(source_root))


def main() -> int:
    cycles = find_cycles()
    if cycles:
        print("ERROR: first-party import cycles detected:", file=sys.stderr)
        for component in cycles:
            print("  - " + " <-> ".join(component), file=sys.stderr)
        return 1
    print("OK: no first-party Python import cycles detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
