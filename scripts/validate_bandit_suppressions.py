# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate that Bandit suppressions are narrow and auditable."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOTS = (
    "src/configstream",
    "scripts",
    "tools",
    "frontend/assets/js",
)
SOURCE_SUFFIXES = {".py", ".js"}
NOSEC_RE = re.compile(r"#\s*nosec(?P<body>[^\r\n]*)")
RULE_RE = re.compile(r"^B\d{3}$")


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


def _rule_tokens(body: str) -> list[str]:
    return [
        token.strip()
        for token in body.replace(",", " ").split()
        if token.strip()
    ]


def validate_bandit_suppressions(
    scan_roots: tuple[str, ...] = DEFAULT_SCAN_ROOTS,
) -> list[str]:
    errors: list[str] = []
    for path in _iter_source_files(scan_roots):
        rel_path = path.relative_to(ROOT)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            errors.append(f"{rel_path}: cannot decode as UTF-8: {exc}")
            continue

        for line_no, line in enumerate(lines, 1):
            match = NOSEC_RE.search(line)
            if not match:
                continue

            tokens = _rule_tokens(match.group("body"))
            if not tokens:
                errors.append(
                    f"{rel_path}:{line_no}: bare Bandit suppression is forbidden; "
                    "pin exact rule IDs such as '# no' + 'sec B603'"
                )
                continue

            invalid = [token for token in tokens if not RULE_RE.fullmatch(token)]
            if invalid:
                errors.append(
                    f"{rel_path}:{line_no}: invalid nosec rule token(s): "
                    f"{', '.join(invalid)}"
                )

            duplicates = sorted(
                {token for token in tokens if tokens.count(token) > 1}
            )
            if duplicates:
                errors.append(
                    f"{rel_path}:{line_no}: duplicate nosec rule token(s): "
                    f"{', '.join(duplicates)}"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional repository-relative files or directories to scan.",
    )
    args = parser.parse_args(argv)

    scan_roots = tuple(args.paths) if args.paths else DEFAULT_SCAN_ROOTS
    errors = validate_bandit_suppressions(scan_roots)
    if errors:
        for error in errors:
            print(error)
        return 1

    print("OK: Bandit suppressions are pinned to explicit rule IDs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
