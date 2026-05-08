# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate generated documentation mirrors stay in sync."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "docs" / "wiki" / "encyclopedia"
MIRROR = ROOT / "docs" / "encyclopedia"


def _relative_files(root: Path) -> set[Path]:
    return {path.relative_to(root) for path in root.rglob("*") if path.is_file()}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_docs_sync() -> list[str]:
    errors: list[str] = []
    canonical_files = _relative_files(CANONICAL)
    mirror_files = _relative_files(MIRROR)

    for missing in sorted(canonical_files - mirror_files):
        errors.append(f"docs/encyclopedia missing mirror file: {missing.as_posix()}")
    for extra in sorted(mirror_files - canonical_files):
        errors.append(f"docs/encyclopedia has unmanaged extra file: {extra.as_posix()}")

    for rel_path in sorted(canonical_files & mirror_files):
        canonical_path = CANONICAL / rel_path
        mirror_path = MIRROR / rel_path
        if _sha256(canonical_path) != _sha256(mirror_path):
            errors.append(f"encyclopedia mirror drift: {rel_path.as_posix()}")

    return errors


def main() -> None:
    errors = validate_docs_sync()
    if errors:
        print("ERROR: documentation mirror validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: docs/encyclopedia mirrors docs/wiki/encyclopedia.")


if __name__ == "__main__":
    main()
