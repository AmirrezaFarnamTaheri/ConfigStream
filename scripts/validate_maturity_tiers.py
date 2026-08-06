# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate product maturity labels and required-release boundaries."""
from __future__ import annotations
import json
from pathlib import Path

ALLOWED_TIERS = {"stable", "beta", "experimental"}
REQUIRED_IDS = {"python-core", "go-native-tester", "public-pages", "browser-reachability-wasm", "rust-ss-checker"}


def validate(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    try:
        data = json.loads((root / "docs/maturity_tiers.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"maturity manifest unreadable: {type(exc).__name__}"]
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, list):
        return ["maturity manifest surfaces must be a list"]
    ids: set[str] = set()
    for index, item in enumerate(surfaces):
        if not isinstance(item, dict):
            errors.append(f"surfaces[{index}] must be an object")
            continue
        surface_id = item.get("id")
        tier = item.get("tier")
        if not isinstance(surface_id, str) or not surface_id:
            errors.append(f"surfaces[{index}] missing id")
            continue
        if surface_id in ids:
            errors.append(f"duplicate maturity surface id: {surface_id}")
        ids.add(surface_id)
        if tier not in ALLOWED_TIERS:
            errors.append(f"{surface_id}: invalid tier {tier!r}")
        if item.get("required_release") is True and tier != "stable":
            errors.append(f"{surface_id}: only stable surfaces may be required for release")
        paths = item.get("paths")
        if not isinstance(paths, list) or not paths:
            errors.append(f"{surface_id}: paths must be a non-empty list")
        else:
            for relative in paths:
                if not isinstance(relative, str) or not (root / relative).exists():
                    errors.append(f"{surface_id}: missing path {relative!r}")
        verification = item.get("verification")
        if not isinstance(verification, list) or not verification:
            errors.append(f"{surface_id}: verification must be declared")
        if tier == "experimental" and not item.get("limitations"):
            errors.append(f"{surface_id}: experimental surface requires explicit limitations")
    for missing in sorted(REQUIRED_IDS - ids):
        errors.append(f"required maturity surface missing: {missing}")
    readme = (root / "README.md").read_text(encoding="utf-8")
    if "## Maturity tiers" not in readme:
        errors.append("README.md missing Maturity tiers section")
    return errors


def main() -> int:
    errors = validate(Path('.'))
    if errors:
        print('ERROR: maturity tier validation failed')
        for error in errors: print(f'  - {error}')
        return 1
    print('OK: maturity tiers and release boundaries are explicit')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
