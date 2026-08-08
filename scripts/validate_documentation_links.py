#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate repository-local Markdown links in maintained documentation."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("#", "http://", "https://", "mailto:", "data:", "javascript:")


def markdown_files(root: Path) -> list[Path]:
    candidates = [root / "README.md", root / "AGENTS.md", root / "GEMINI.md"]
    candidates.extend(sorted((root / "docs").rglob("*.md")))
    return [path for path in candidates if path.exists()]


def validate(root: Path = ROOT) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    for path in markdown_files(root):
        text = path.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(text):
            raw_target = match.group(1).strip().split(maxsplit=1)[0].strip("<>")
            if not raw_target or raw_target.startswith(SKIP_PREFIXES):
                continue
            target = unquote(raw_target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            if not resolved.exists():
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{path.relative_to(root).as_posix()}:{line}: missing local link target {target}"
                )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("ERROR: documentation link validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        f"OK: local links validated across {len(markdown_files(ROOT))} Markdown files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
