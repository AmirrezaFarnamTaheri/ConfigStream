# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate the project claim ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validation_utils import load_json_object, is_nonempty_string


ENCODING = "utf-8"
LEDGER_PATH = ROOT / "docs" / "claim_ledger.json"

REQUIRED_FIELDS = {
    "id",
    "claim",
    "source",
    "product_area",
    "status",
    "owner",
    "tests",
    "frontend_surface",
    "output_artifact",
    "docs",
    "changelog",
    "cleanup_decision",
}

VALID_STATUSES = {
    "complete",
    "partial",
    "planned",
    "experimental",
    "deprecated",
    "removed",
}




def _is_string_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(is_nonempty_string(item) for item in value)
    )


def validate_claim_ledger(path: Path = LEDGER_PATH) -> list[str]:
    errors: list[str] = []
    try:
        data = load_json_object(path, root_label="claim ledger")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"claim ledger cannot be read: {exc}"]

    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["claim ledger must contain a non-empty claims list"]

    seen_ids: set[str] = set()
    complete_count = 0
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be an object")
            continue

        missing = REQUIRED_FIELDS - set(claim)
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")

        claim_id = claim.get("id")
        if not is_nonempty_string(claim_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif claim_id in seen_ids:
            errors.append(f"duplicate claim id: {claim_id}")
        else:
            seen_ids.add(str(claim_id))

        for field in ("claim", "source", "product_area", "owner", "cleanup_decision"):
            if not is_nonempty_string(claim.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")

        status = claim.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"{prefix}.status is invalid: {status}")

        if not isinstance(claim.get("tests"), list):
            errors.append(f"{prefix}.tests must be a list")
        if not isinstance(claim.get("docs"), list):
            errors.append(f"{prefix}.docs must be a list")

        if status == "complete":
            complete_count += 1
            if not _is_string_list(claim.get("tests")):
                errors.append(f"{prefix} complete claim must list proving tests")
            if not _is_string_list(claim.get("docs")):
                errors.append(f"{prefix} complete claim must list updated docs")
            if not is_nonempty_string(claim.get("changelog")):
                errors.append(f"{prefix} complete claim must name a changelog entry")

    if complete_count == 0:
        errors.append("claim ledger must contain at least one complete claim")

    return errors


def main() -> None:
    errors = validate_claim_ledger()
    if errors:
        print("ERROR: claim ledger validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: claim ledger validated.")


if __name__ == "__main__":
    main()
