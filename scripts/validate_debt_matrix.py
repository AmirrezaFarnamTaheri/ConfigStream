# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate debt matrix artifacts are portable and non-self-referential."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEBT_JSON = ROOT / "docs" / "debt_matrix.json"
DEBT_MD = ROOT / "docs" / "DEBT_MATRIX.md"
GENERATED_PATHS = {"docs/debt_matrix.json", "docs/DEBT_MATRIX.md"}
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:/")


def _load_json() -> dict:
    data = json.loads(DEBT_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("debt matrix JSON must be an object")
    return data


def validate_debt_matrix() -> list[str]:
    errors: list[str] = []
    data = _load_json()
    entries = data.get("entries")
    if not isinstance(entries, list):
        return ["docs/debt_matrix.json missing entries list"]

    summary = data.get("summary")
    if not isinstance(summary, dict):
        errors.append("docs/debt_matrix.json missing summary object")
    elif "categories" not in summary:
        errors.append("docs/debt_matrix.json missing category summary")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry {index} is not an object")
            continue
        path = str(entry.get("path", ""))
        if not path:
            errors.append(f"entry {index} missing path")
            continue
        if WINDOWS_ABSOLUTE_RE.match(path) or path.startswith("/"):
            errors.append(f"entry {index} has absolute path: {path}")
        if "\\" in path:
            errors.append(f"entry {index} uses backslashes: {path}")
        if path in GENERATED_PATHS:
            errors.append(f"entry {index} self-references generated artifact: {path}")
        if "category" not in entry:
            errors.append(f"entry {index} missing category")

    md_text = DEBT_MD.read_text(encoding="utf-8")
    if "D:/GitHub/ConfigStream" in md_text or str(ROOT).replace("\\", "/") in md_text:
        errors.append("docs/DEBT_MATRIX.md contains machine-local absolute paths")
    if "## Categories" not in md_text:
        errors.append("docs/DEBT_MATRIX.md missing category summary")
    for generated in GENERATED_PATHS:
        if f"`{generated}`" in md_text:
            errors.append(f"docs/DEBT_MATRIX.md self-references {generated}")

    return errors


def main() -> None:
    errors = validate_debt_matrix()
    if errors:
        print("ERROR: debt matrix validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: debt matrix artifacts are portable.")


if __name__ == "__main__":
    main()
