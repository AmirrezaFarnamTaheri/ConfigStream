# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate the public output matrix against the Pages artifact contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_pages_artifact import (
    REQUIRED_EXISTS,
    REQUIRED_NONEMPTY,
    REQUIRED_ZIP_MEMBERS,
)

MATRIX_PATH = ROOT / "docs" / "output_matrix.json"
VALID_CATEGORIES = {
    "control",
    "api",
    "frontend",
    "docs",
    "analytics",
    "side-product",
    "subscription",
}
VALID_FORMATS = {
    "base64",
    "html",
    "json",
    "markdown",
    "text",
    "yaml",
    "zip",
}
EXPECTED_ZIP_OPTIONAL_PATTERNS = {
    "side_products.zip": ("openvpn/*.ovpn", "wireguard/*.conf"),
    "side_products-dns-safe.zip": ("openvpn/*.ovpn", "wireguard/*.conf"),
    "side_products-dns-hardened.zip": ("openvpn/*.ovpn", "wireguard/*.conf"),
}
REQUIRED_FIELDS = {
    "path",
    "family",
    "category",
    "format",
    "required",
    "nonempty",
    "schema_validation",
    "degraded_valid",
    "notes",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding=ENCODING) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("output matrix root must be an object")
    return data


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_safe_zip_member_pattern(value: str) -> bool:
    parts = [part for part in value.replace("\\", "/").split("/") if part]
    return (
        "/" in value
        and "*" in value
        and "\\" not in value
        and not value.startswith("/")
        and not value.startswith("../")
        and "/../" not in value
        and ".." not in parts
        and not any(":" in part for part in parts)
    )


def validate_output_matrix(path: Path = MATRIX_PATH) -> list[str]:
    errors: list[str] = []
    try:
        data = _load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"output matrix cannot be read: {exc}"]

    outputs = data.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        return ["output matrix must contain a non-empty outputs list"]

    seen_paths: set[str] = set()
    matrix_paths: set[str] = set()
    matrix_nonempty: set[str] = set()
    schema_validated: set[str] = set()
    degraded_valid: set[str] = set()
    matrix_zip_members: dict[str, tuple[str, ...]] = {}
    matrix_zip_patterns: dict[str, tuple[str, ...]] = {}

    for index, item in enumerate(outputs):
        prefix = f"outputs[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue

        missing = REQUIRED_FIELDS - set(item)
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")

        rel_path = item.get("path")
        if not _is_nonempty_string(rel_path):
            errors.append(f"{prefix}.path must be a non-empty string")
            continue
        if "\\" in rel_path or rel_path.startswith("/") or ".." in rel_path.split("/"):
            errors.append(f"{prefix}.path must be a safe repo-relative POSIX path")
        if rel_path in seen_paths:
            errors.append(f"duplicate output path: {rel_path}")
        seen_paths.add(str(rel_path))
        matrix_paths.add(str(rel_path))

        if not _is_nonempty_string(item.get("family")):
            errors.append(f"{prefix}.family must be a non-empty string")
        if item.get("category") not in VALID_CATEGORIES:
            errors.append(f"{prefix}.category is invalid: {item.get('category')}")
        if item.get("format") not in VALID_FORMATS:
            errors.append(f"{prefix}.format is invalid: {item.get('format')}")
        if not _is_nonempty_string(item.get("notes")):
            errors.append(f"{prefix}.notes must be a non-empty string")

        for field in ("required", "nonempty", "schema_validation", "degraded_valid"):
            if not isinstance(item.get(field), bool):
                errors.append(f"{prefix}.{field} must be boolean")

        if item.get("nonempty") is True:
            matrix_nonempty.add(str(rel_path))
        if item.get("schema_validation") is True:
            schema_validated.add(str(rel_path))
        if item.get("degraded_valid") is True:
            degraded_valid.add(str(rel_path))
        zip_members = item.get("zip_required_members")
        if zip_members is not None:
            if not (
                isinstance(zip_members, list)
                and all(_is_nonempty_string(member) for member in zip_members)
            ):
                errors.append(f"{prefix}.zip_required_members must be a string list")
            else:
                matrix_zip_members[str(rel_path)] = tuple(
                    str(member) for member in zip_members
                )

        zip_patterns = item.get("zip_optional_member_patterns")
        if zip_patterns is not None:
            if not (
                isinstance(zip_patterns, list)
                and all(_is_nonempty_string(pattern) for pattern in zip_patterns)
            ):
                errors.append(
                    f"{prefix}.zip_optional_member_patterns must be a string list"
                )
            else:
                patterns = tuple(str(pattern) for pattern in zip_patterns)
                matrix_zip_patterns[str(rel_path)] = patterns
                for pattern in patterns:
                    if not _is_safe_zip_member_pattern(pattern):
                        errors.append(
                            f"{prefix}.zip_optional_member_patterns has unsafe pattern: "
                            f"{pattern}"
                        )

    required_paths = set(REQUIRED_EXISTS)
    required_nonempty = set(REQUIRED_NONEMPTY)
    missing_from_matrix = required_paths - matrix_paths
    extra_required = matrix_paths - required_paths
    if missing_from_matrix:
        errors.append(
            "output matrix missing Pages-required outputs: "
            + ", ".join(sorted(missing_from_matrix))
        )
    if extra_required:
        errors.append(
            "output matrix lists outputs not required by Pages validator: "
            + ", ".join(sorted(extra_required))
        )

    nonempty_mismatch = required_nonempty ^ matrix_nonempty
    if nonempty_mismatch:
        errors.append(
            "output matrix nonempty flags drift from Pages validator: "
            + ", ".join(sorted(nonempty_mismatch))
        )

    for rel_path in ("artifact_manifest.json", "health.json", "metadata.json", "proxies.json"):
        if rel_path not in schema_validated:
            errors.append(f"{rel_path} must be marked schema_validation=true")

    for rel_path in required_paths:
        if rel_path not in degraded_valid:
            errors.append(f"{rel_path} must be marked degraded_valid=true")

    for rel_path, members in REQUIRED_ZIP_MEMBERS.items():
        if matrix_zip_members.get(rel_path) != members:
            errors.append(
                f"{rel_path} zip_required_members drift from Pages validator"
            )
    for rel_path in sorted(set(matrix_zip_members) - set(REQUIRED_ZIP_MEMBERS)):
        errors.append(f"{rel_path} declares unexpected zip_required_members")

    for rel_path, patterns in EXPECTED_ZIP_OPTIONAL_PATTERNS.items():
        if matrix_zip_patterns.get(rel_path) != patterns:
            errors.append(
                f"{rel_path} zip_optional_member_patterns drift from generator contract"
            )
    for rel_path in sorted(
        set(matrix_zip_patterns) - set(EXPECTED_ZIP_OPTIONAL_PATTERNS)
    ):
        errors.append(f"{rel_path} declares unexpected zip_optional_member_patterns")

    return errors


def main() -> None:
    errors = validate_output_matrix()
    if errors:
        print("ERROR: output matrix validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: output matrix validated.")


if __name__ == "__main__":
    main()
