# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate and optionally inject frontend production secrets.

This guard keeps deploy artifacts from silently shipping placeholder verification
or steganography keys. It is intentionally small and dependency-free so it can
run in CI before GitHub Pages upload.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PUBLIC_KEY_PLACEHOLDER_MARKERS = ("79e/79e/", "PLACEHOLDER_PUBLIC_KEY")
STEGO_KEY_PLACEHOLDER = "PLACEHOLDER_KEY_INJECTED_BY_CI"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def inject_frontend_keys(root: Path, env: dict[str, str]) -> list[str]:
    changes: list[str] = []
    constants_path = root / "assets" / "js" / "constants.js"
    stego_path = root / "assets" / "js" / "stego.js"

    public_key = env.get("CS_PUBLIC_KEY", "").strip()
    if public_key and constants_path.exists():
        content = _read(constants_path)
        updated = re.sub(
            r'(PUBLIC_KEY\s*:\s*)"[^"]*"',
            lambda match: f"{match.group(1)}{_js_string(public_key)}",
            content,
            count=1,
        )
        if updated != content:
            _write(constants_path, updated)
            changes.append(str(constants_path))

    stego_key = (env.get("STEGO_KEY") or env.get("CONFIG_STREAM_KEY") or "").strip()
    if stego_key and stego_path.exists():
        content = _read(stego_path)
        updated = re.sub(
            r'(const\s+SECRET_KEY\s*=\s*)"[^"]*"',
            lambda match: f"{match.group(1)}{_js_string(stego_key)}",
            content,
            count=1,
        )
        if updated != content:
            _write(stego_path, updated)
            changes.append(str(stego_path))

    return changes


def validate_frontend_placeholders(root: Path, *, strict: bool = False) -> list[str]:
    errors: list[str] = []
    constants_path = root / "assets" / "js" / "constants.js"
    stego_path = root / "assets" / "js" / "stego.js"

    if not constants_path.exists():
        errors.append(f"Missing frontend constants file: {constants_path}")
    else:
        constants = _read(constants_path)
        if any(marker in constants for marker in PUBLIC_KEY_PLACEHOLDER_MARKERS):
            errors.append(
                "Frontend PUBLIC_KEY placeholder remains in assets/js/constants.js"
            )

    if not stego_path.exists():
        if strict:
            errors.append(f"Missing frontend stego file: {stego_path}")
    else:
        stego = _read(stego_path)
        if STEGO_KEY_PLACEHOLDER in stego:
            errors.append(
                "Frontend STEGO_KEY placeholder remains in assets/js/stego.js"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Frontend artifact root to validate")
    parser.add_argument(
        "--inject-env",
        action="store_true",
        help="Inject CS_PUBLIC_KEY and STEGO_KEY/CONFIG_STREAM_KEY from environment.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on missing security-bearing frontend files.",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: frontend root does not exist: {root}", file=sys.stderr)
        return 2

    if args.inject_env:
        changes = inject_frontend_keys(root, os.environ)
        if changes:
            print(f"Injected frontend keys into {len(changes)} file(s).")

    errors = validate_frontend_placeholders(root, strict=bool(args.strict))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("OK: frontend production placeholders validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
