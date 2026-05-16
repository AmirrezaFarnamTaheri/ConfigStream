# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate docs/capability_registry.json against implementation proof."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "capability_registry.json"
CLAIM_LEDGER_PATH = ROOT / "docs" / "claim_ledger.json"

REQUIRED_FIELDS = {
    "id",
    "title",
    "status",
    "product_area",
    "owner",
    "implementation",
    "claim_ids",
    "tests",
    "docs",
    "outputs",
    "limitations",
    "cleanup_decision",
}

VALID_STATUSES = {
    "stable",
    "partial",
    "experimental",
    "planned",
    "deprecated",
    "removed",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding=ENCODING) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be an object")
    return data


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(_is_nonempty_string(item) for item in value)


def _path_exists(path_text: str) -> bool:
    path = ROOT / path_text
    if any(char in path_text for char in "*?["):
        return bool(list(ROOT.glob(path_text)))
    return path.exists()


def _complete_claim_ids() -> set[str]:
    ledger = _load_json(CLAIM_LEDGER_PATH)
    claims = ledger.get("claims", [])
    if not isinstance(claims, list):
        return set()
    return {
        str(claim["id"])
        for claim in claims
        if isinstance(claim, dict)
        and claim.get("status") == "complete"
        and _is_nonempty_string(claim.get("id"))
    }


def validate_capability_registry(path: Path = REGISTRY_PATH) -> list[str]:
    errors: list[str] = []
    try:
        data = _load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"capability registry cannot be read: {exc}"]

    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        return ["capability registry must contain a non-empty capabilities list"]

    complete_claims = _complete_claim_ids()
    seen_ids: set[str] = set()
    stable_count = 0

    for index, capability in enumerate(capabilities):
        prefix = f"capabilities[{index}]"
        if not isinstance(capability, dict):
            errors.append(f"{prefix} must be an object")
            continue

        missing = REQUIRED_FIELDS - set(capability)
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")

        capability_id = capability.get("id")
        if not _is_nonempty_string(capability_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif capability_id in seen_ids:
            errors.append(f"duplicate capability id: {capability_id}")
        else:
            seen_ids.add(str(capability_id))

        for field in ("title", "product_area", "owner", "cleanup_decision"):
            if not _is_nonempty_string(capability.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")

        status = capability.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"{prefix}.status is invalid: {status}")

        for field in ("implementation", "claim_ids", "tests", "docs", "outputs"):
            if not isinstance(capability.get(field), list):
                errors.append(f"{prefix}.{field} must be a list")

        if not _is_string_list(capability.get("limitations")):
            errors.append(f"{prefix}.limitations must list explicit limitations")

        if status == "stable":
            stable_count += 1
            for field in ("implementation", "claim_ids", "tests", "docs"):
                if not _is_string_list(capability.get(field)):
                    errors.append(f"{prefix} stable capability must list {field}")

            for claim_id in capability.get("claim_ids", []):
                if claim_id not in complete_claims:
                    errors.append(
                        f"{prefix} stable capability references non-complete claim: "
                        f"{claim_id}"
                    )

            for field in ("implementation", "tests", "docs"):
                for path_text in capability.get(field, []):
                    if isinstance(path_text, str) and not _path_exists(path_text):
                        errors.append(f"{prefix}.{field} path is missing: {path_text}")

    if stable_count == 0:
        errors.append("capability registry must contain at least one stable capability")

    return errors


def main() -> None:
    errors = validate_capability_registry()
    if errors:
        print("ERROR: capability registry validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: capability registry validated.")


if __name__ == "__main__":
    main()
