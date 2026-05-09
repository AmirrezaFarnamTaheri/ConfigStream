# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate and optionally generate frontend runtime config.

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


def _runtime_config_content(env: dict[str, str]) -> str:
    public_key = env.get("CS_PUBLIC_KEY", "").strip()
    stego_key = (env.get("STEGO_KEY") or env.get("CONFIG_STREAM_KEY") or "").strip()
    ipns_key = env.get("CS_IPNS_KEY", "").strip()
    return "\n".join(
        [
            "// Generated during ConfigStream Pages deploy. Do not edit by hand.",
            "(function(global) {",
            "  global.CS_RUNTIME_CONFIG = {",
            f"    PUBLIC_KEY: {_js_string(public_key)},",
            f"    STEGO_KEY: {_js_string(stego_key)},",
            f"    IPNS_KEY: {_js_string(ipns_key)}",
            "  };",
            "})(typeof window !== 'undefined' ? window : self);",
            "",
        ]
    )


def inject_frontend_keys(root: Path, env: dict[str, str]) -> list[str]:
    changes: list[str] = []
    runtime_config_path = root / "assets" / "js" / "runtime-config.js"
    runtime_config_path.parent.mkdir(parents=True, exist_ok=True)
    content = _runtime_config_content(env)
    if not runtime_config_path.exists() or _read(runtime_config_path) != content:
        _write(runtime_config_path, content)
        changes.append(str(runtime_config_path))

    return changes


def validate_frontend_placeholders(root: Path, *, strict: bool = False) -> list[str]:
    errors: list[str] = []
    constants_path = root / "assets" / "js" / "constants.js"
    stego_path = root / "assets" / "js" / "stego.js"
    runtime_config_path = root / "assets" / "js" / "runtime-config.js"

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

    if strict:
        if not runtime_config_path.exists():
            errors.append(f"Missing frontend runtime config file: {runtime_config_path}")
        else:
            runtime_config = _read(runtime_config_path)
            if any(marker in runtime_config for marker in PUBLIC_KEY_PLACEHOLDER_MARKERS):
                errors.append(
                    "Frontend PUBLIC_KEY placeholder remains in assets/js/runtime-config.js"
                )
            if STEGO_KEY_PLACEHOLDER in runtime_config:
                errors.append(
                    "Frontend STEGO_KEY placeholder remains in assets/js/runtime-config.js"
                )
            if re.search(r'PUBLIC_KEY:\s*""', runtime_config):
                errors.append("Frontend PUBLIC_KEY is missing in assets/js/runtime-config.js")
            if re.search(r'STEGO_KEY:\s*""', runtime_config):
                errors.append("Frontend STEGO_KEY is missing in assets/js/runtime-config.js")

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
            print(f"Generated frontend runtime config in {len(changes)} file(s).")

    errors = validate_frontend_placeholders(root, strict=bool(args.strict))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("OK: frontend production placeholders validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
