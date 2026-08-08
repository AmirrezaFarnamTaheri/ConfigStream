# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate docs/module_ownership.json and removed-module import boundaries."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validation_utils import load_json_object, is_nonempty_string

ENCODING = "utf-8"
MAP_PATH = ROOT / "docs" / "module_ownership.json"
SCAN_DIRS = ("src", "scripts", "tests", "tools")
REQUIRED_MODULE_FIELDS = {
    "path",
    "domain",
    "owner",
    "public_apis",
    "internal_only_apis",
    "disallowed_duplicates",
    "replacement_for_removed_modules",
    "tests",
    "docs",
}
REQUIRED_REMOVED_FIELDS = {"path", "import_names", "replacement"}


def _is_string_list(value: object, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(is_nonempty_string(item) for item in value)
    )


def _path_exists(path_text: str) -> bool:
    return (ROOT / path_text).exists()


def _iter_python_files() -> Iterable[Path]:
    for dirname in SCAN_DIRS:
        root = ROOT / dirname
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in {".venv", "__pycache__"} for part in path.parts):
                continue
            yield path


def _imported_modules(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding=ENCODING))
    except (OSError, SyntaxError):
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _matches_removed_import(imported: str, removed: str) -> bool:
    return imported == removed or imported.startswith(f"{removed}.")


def validate_module_ownership(path: Path = MAP_PATH) -> list[str]:
    errors: list[str] = []
    try:
        data = load_json_object(path, root_label="module ownership")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"module ownership map cannot be read: {exc}"]

    modules = data.get("modules")
    removed_modules = data.get("removed_modules")
    if not isinstance(modules, list) or not modules:
        return ["module ownership map must contain a non-empty modules list"]
    if not isinstance(removed_modules, list) or not removed_modules:
        errors.append("module ownership map must contain removed_modules")
        removed_modules = []

    seen_paths: set[str] = set()
    for index, module in enumerate(modules):
        prefix = f"modules[{index}]"
        if not isinstance(module, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = REQUIRED_MODULE_FIELDS - set(module)
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")
        path_text = module.get("path")
        if not is_nonempty_string(path_text):
            errors.append(f"{prefix}.path must be a non-empty string")
        else:
            if path_text in seen_paths:
                errors.append(f"duplicate module path: {path_text}")
            seen_paths.add(str(path_text))
            if not _path_exists(str(path_text)):
                errors.append(f"{prefix}.path is missing: {path_text}")
        for field in ("domain", "owner"):
            if not is_nonempty_string(module.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        for field in (
            "public_apis",
            "internal_only_apis",
            "disallowed_duplicates",
            "replacement_for_removed_modules",
        ):
            if not _is_string_list(module.get(field)):
                errors.append(f"{prefix}.{field} must be a list of strings")
        for field in ("tests", "docs"):
            if not _is_string_list(module.get(field), allow_empty=False):
                errors.append(f"{prefix}.{field} must list proof paths")
                continue
            for proof_path in module.get(field, []):
                if isinstance(proof_path, str) and not _path_exists(proof_path):
                    errors.append(f"{prefix}.{field} path is missing: {proof_path}")

    removed_imports: set[str] = set()
    for index, removed in enumerate(removed_modules):
        prefix = f"removed_modules[{index}]"
        if not isinstance(removed, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = REQUIRED_REMOVED_FIELDS - set(removed)
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")
        removed_path = removed.get("path")
        if not is_nonempty_string(removed_path):
            errors.append(f"{prefix}.path must be a non-empty string")
        elif _path_exists(str(removed_path)):
            errors.append(f"{prefix}.path has been recreated: {removed_path}")
        if not _is_string_list(removed.get("import_names")):
            errors.append(f"{prefix}.import_names must be a list of strings")
        else:
            removed_imports.update(str(name) for name in removed["import_names"])
        if not is_nonempty_string(removed.get("replacement")):
            errors.append(f"{prefix}.replacement must be a non-empty string")

    for py_file in _iter_python_files():
        rel_path = py_file.relative_to(ROOT).as_posix()
        for imported in _imported_modules(py_file):
            for removed_import in removed_imports:
                if _matches_removed_import(imported, removed_import):
                    errors.append(f"{rel_path} imports removed module {removed_import}")

    return errors


def main() -> None:
    errors = validate_module_ownership()
    if errors:
        print("ERROR: module ownership validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: module ownership map validated.")


if __name__ == "__main__":
    main()
