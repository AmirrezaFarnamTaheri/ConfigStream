# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate and optionally generate the public frontend runtime config.

Only public verification and routing material may be written to the static
artifact. Symmetric encryption keys are explicitly forbidden because anything
shipped to a browser is public information.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Mapping

PUBLIC_KEY_PLACEHOLDER_MARKERS = ("79e/79e/", "PLACEHOLDER_PUBLIC_KEY")
STEGO_KEY_PLACEHOLDER = "PLACEHOLDER_KEY_INJECTED_BY_CI"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _runtime_config_content(env: Mapping[str, str]) -> str:
    public_key = env.get("CS_PUBLIC_KEY", "").strip()
    ipns_key = env.get("CS_IPNS_KEY", "").strip()
    return "\n".join(
        [
            "// Generated during ConfigStream artifact preparation. Do not edit by hand.",
            "(function(global) {",
            "  global.CS_RUNTIME_CONFIG = {",
            f"    PUBLIC_KEY: {_js_string(public_key)},",
            f"    IPNS_KEY: {_js_string(ipns_key)}",
            "  };",
            "})(typeof window !== 'undefined' ? window : self);",
            "",
        ]
    )


def inject_frontend_keys(root: Path, env: Mapping[str, str]) -> list[str]:
    """Write public runtime material while refusing symmetric secrets."""

    if any(
        (env.get(name) or "").strip() for name in ("STEGO_KEY", "CONFIG_STREAM_KEY")
    ):
        raise ValueError("symmetric frontend keys must not be published")
    runtime_config_path = root / "assets" / "js" / "runtime-config.js"
    runtime_config_path.parent.mkdir(parents=True, exist_ok=True)
    content = _runtime_config_content(env)
    if runtime_config_path.exists() and _read(runtime_config_path) == content:
        return []
    _write(runtime_config_path, content)
    return [str(runtime_config_path)]


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

    if stego_path.exists() and STEGO_KEY_PLACEHOLDER in _read(stego_path):
        errors.append("Frontend STEGO_KEY placeholder remains in assets/js/stego.js")

    if strict:
        if not runtime_config_path.exists():
            errors.append(
                f"Missing frontend runtime config file: {runtime_config_path}"
            )
        else:
            runtime_config = _read(runtime_config_path)
            if any(
                marker in runtime_config for marker in PUBLIC_KEY_PLACEHOLDER_MARKERS
            ):
                errors.append(
                    "Frontend PUBLIC_KEY placeholder remains in assets/js/runtime-config.js"
                )
            if STEGO_KEY_PLACEHOLDER in runtime_config:
                errors.append(
                    "Frontend STEGO_KEY placeholder remains in assets/js/runtime-config.js"
                )
            if re.search(r"\b(?:STEGO_KEY|CONFIG_STREAM_KEY)\s*:", runtime_config):
                errors.append(
                    "Frontend runtime config must not contain a symmetric key field"
                )
            if re.search(r'PUBLIC_KEY:\s*""', runtime_config):
                errors.append(
                    "Frontend PUBLIC_KEY is missing in assets/js/runtime-config.js"
                )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Frontend artifact root to validate")
    parser.add_argument(
        "--inject-env",
        action="store_true",
        help="Inject public CS_PUBLIC_KEY and CS_IPNS_KEY values from the environment.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on missing security-bearing frontend files or public verification key.",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: frontend root does not exist: {root}", file=sys.stderr)
        return 2

    if args.inject_env:
        try:
            changes = inject_frontend_keys(root, os.environ)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
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
