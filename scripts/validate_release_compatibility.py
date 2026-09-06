# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate release compatibility metadata against governed runtime contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def validate(artifact_dir: Path, repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    try:
        runtime = _load_object(repo_root / "config/runtime-versions.json")
        compatibility = _load_object(artifact_dir / "format_compatibility.json")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"compatibility metadata unreadable: {type(exc).__name__}: {exc}"]

    sing_box_runtime = runtime.get("sing_box")
    targets = compatibility.get("targets")
    if not isinstance(sing_box_runtime, dict):
        return ["runtime-versions.json must define sing_box"]
    if not isinstance(targets, dict):
        return ["format_compatibility.json targets must be an object"]

    governed = str(sing_box_runtime.get("release_validator") or "").strip()
    sing_box = targets.get("sing-box")
    if not isinstance(sing_box, dict):
        errors.append("format compatibility is missing sing-box target")
    elif str(sing_box.get("target") or "").strip() != governed:
        errors.append(
            "sing-box compatibility target does not match governed release validator: "
            f"{sing_box.get('target')!r} != {governed!r}"
        )

    sip008 = targets.get("sip008")
    if not isinstance(sip008, dict):
        errors.append("format compatibility is missing SIP008 target")
    else:
        if sip008.get("dns_hardened_resolver_policy") != "unsupported_by_sip008":
            errors.append(
                "SIP008 must explicitly declare encrypted resolver policy unsupported"
            )
        safe_name = str(sip008.get("dns_safe_endpoint_variant") or "")
        if safe_name != "sip008-dns-safe.json":
            errors.append("SIP008 DNS-safe endpoint variant must be sip008-dns-safe.json")
        elif not (artifact_dir / safe_name).is_file():
            errors.append(f"SIP008 DNS-safe endpoint variant is missing: {safe_name}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    errors = validate(args.artifact_dir, args.repo_root)
    if errors:
        print("ERROR: release compatibility validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: release compatibility metadata matches governed runtime contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
