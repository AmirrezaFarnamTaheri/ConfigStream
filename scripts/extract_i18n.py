# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regenerate runtime i18n bundles from their editable raw sources.

The frontend loads translations at runtime from
``frontend/assets/i18n/<lang>.json`` (see ``frontend/assets/js/i18n.js``).
The editable sources live next to them as ``<lang>_raw.txt`` in a JSONC
dialect (JSON with ``/* ... */`` and ``// ...`` comments plus optional
trailing commas). This script converts every raw source into its strict
JSON runtime bundle.

Usage:
    python scripts/extract_i18n.py [--check]

``--check`` validates that the committed bundles are in sync with the raw
sources without writing anything (useful for CI), exiting non-zero on
drift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
I18N_DIR = REPO_ROOT / "frontend" / "assets" / "i18n"


def _strip_jsonc(text: str) -> str:
    """Strip ``/* */`` and ``// `` comments and trailing commas.

    Comment markers inside double-quoted JSON strings are preserved.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            end = text.find("\n", i)
            i = n if end == -1 else end
            continue
        out.append(ch)
        i += 1
    cleaned = "".join(out)
    # Remove trailing commas before closing braces/brackets.
    cleaned = re.sub(r",\s*([\]\}])", r"\1", cleaned)
    return cleaned


def load_raw_bundle(raw_path: Path) -> dict:
    """Parse a ``<lang>_raw.txt`` JSONC file into a dict."""
    text = raw_path.read_text(encoding="utf-8")
    data = json.loads(_strip_jsonc(text))
    if not isinstance(data, dict):
        raise ValueError(f"{raw_path.name}: expected a JSON object at top level")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed bundles match raw sources without writing",
    )
    args = parser.parse_args(argv)

    if not I18N_DIR.is_dir():
        print(f"ERROR: i18n directory not found: {I18N_DIR}", file=sys.stderr)
        return 1

    raw_files = sorted(I18N_DIR.glob("*_raw.txt"))
    if not raw_files:
        print(f"ERROR: no *_raw.txt sources found in {I18N_DIR}", file=sys.stderr)
        return 1

    failures = 0
    drift = 0
    for raw_path in raw_files:
        lang_code = raw_path.name[: -len("_raw.txt")]
        try:
            data = load_raw_bundle(raw_path)
        except ValueError as e:
            print(f"Failed to parse {raw_path.name}: {e}", file=sys.stderr)
            failures += 1
            continue

        out_path = I18N_DIR / f"{lang_code}.json"
        rendered = json.dumps(data, indent=4, ensure_ascii=False) + "\n"

        if args.check:
            current = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
            try:
                in_sync = out_path.exists() and json.loads(current) == data
            except ValueError:
                in_sync = False
            if in_sync:
                print(f"OK: {lang_code}.json in sync")
            else:
                print(f"DRIFT: {lang_code}.json out of sync with {raw_path.name}")
                drift += 1
        else:
            out_path.write_text(rendered, encoding="utf-8")
            print(f"Extracted {lang_code}.json ({len(data)} keys)")

    if failures:
        return 1
    if args.check and drift:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
