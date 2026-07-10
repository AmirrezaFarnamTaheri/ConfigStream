#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check SPDX license headers on first-party Python/Go scripts."""

from __future__ import annotations
import logging

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPDX_HEADER_MARKER = "SPDX-License-Identifier:"


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for base, pattern in (
        (ROOT / "src", "*.py"),
        (ROOT / "src", "*.go"),
        (ROOT / "scripts", "*.py"),
    ):
        if not base.exists():
            continue
        files.extend(base.rglob(pattern))
    return sorted(set(files))


def _has_spdx_header(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
        return False
    head = "\n".join(lines[:5])
    return SPDX_HEADER_MARKER in head


def main() -> int:
    missing = [p for p in _iter_files() if not _has_spdx_header(p)]
    if missing:
        print("Missing SPDX headers:")
        for path in missing:
            print(f"- {path.relative_to(ROOT).as_posix()}")
        return 1
    print("SPDX header check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
