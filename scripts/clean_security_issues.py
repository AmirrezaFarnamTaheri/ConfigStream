#!/usr/bin/env python3
"""
Utility to remove configs with specific security issues from the output/full/all.json file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Remove config dictionaries whose security_issues contain the target phrase.")
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to the JSON file (e.g., output/full/all.json).",
    )
    parser.add_argument(
        "--phrase",
        default="All test URLs failed",
        help="Security issue phrase to match (default: %(default)s).",
    )
    parser.add_argument(
        "--create-backup",
        action="store_true",
        help="Save a .bak copy of the original file before writing changes.",
    )
    return parser.parse_args()


def load_json(path: Path) -> tuple[str, list[dict[str, Any]]]:
    original_text = path.read_text(encoding="utf-8")
    data = json.loads(original_text)
    if not isinstance(data, list):
        raise ValueError(f"Expected top-level array in {path}")
    return original_text, data


def main() -> int:
    args = parse_args()
    input_path: Path = args.input_path

    if not input_path.exists():
        print(f"Input file {input_path} does not exist.", file=sys.stderr)
        return 1

    try:
        original_text, data = load_json(input_path)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Failed to load JSON from {input_path}: {exc}", file=sys.stderr)
        return 1

    phrase = args.phrase
    filtered = [entry for entry in data if phrase not in (entry.get("security_issues") or [])]
    removed = len(data) - len(filtered)

    if removed == 0:
        print("No matching entries found; file left unchanged.")
        return 0

    if args.create_backup:
        backup_path = input_path.with_suffix(input_path.suffix + ".bak")
        backup_path.write_text(original_text, encoding="utf-8")
        print(f"Backup written to {backup_path}")

    with input_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(filtered, handle, ensure_ascii=True, indent=2)
        handle.write("\n")

    print(
        f"Removed {removed} entries containing '{phrase}'. "
        f"Updated file now has {len(filtered)} entries."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
