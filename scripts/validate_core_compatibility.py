# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate docs/core_compatibility_report.json against output_matrix truth."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ENCODING = "utf-8"
ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "core_compatibility_report.json"
OUTPUT_MATRIX_PATH = ROOT / "docs" / "output_matrix.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding=ENCODING) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be an object")
    return data


def _output_items() -> dict[str, dict[str, Any]]:
    matrix = _load_json(OUTPUT_MATRIX_PATH)
    outputs = matrix.get("outputs", [])
    if not isinstance(outputs, list):
        return {}
    return {
        str(item["path"]): item
        for item in outputs
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }


def _core_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    entries = data.get("core_formats")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def validate_core_compatibility(path: Path = REPORT_PATH) -> list[str]:
    errors: list[str] = []
    try:
        data = _load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"core compatibility report cannot be read: {exc}"]

    outputs = _output_items()
    entries = _core_entries(data)
    if not entries:
        return ["core compatibility report must contain core_formats"]

    seen_cores: set[str] = set()
    for index, entry in enumerate(entries):
        prefix = f"core_formats[{index}]"
        core = entry.get("core")
        if not isinstance(core, str) or not core:
            errors.append(f"{prefix}.core must be a non-empty string")
            continue
        if core in seen_cores:
            errors.append(f"duplicate core compatibility entry: {core}")
        seen_cores.add(core)

        pipeline_outputs = entry.get("pipeline_outputs")
        if not isinstance(pipeline_outputs, list):
            errors.append(f"{prefix}.pipeline_outputs must be a list")
            continue
        for output in pipeline_outputs:
            if not isinstance(output, str) or not output:
                errors.append(f"{prefix}.pipeline_outputs contains invalid value")
            elif output not in outputs:
                errors.append(
                    f"{prefix}.pipeline_outputs references missing output: {output}"
                )
            elif core in {"clash", "sing-box"}:
                item = outputs[output]
                expected_core = "sing-box" if core == "sing-box" else "clash"
                if item.get("core_format") != expected_core:
                    errors.append(
                        f"{prefix}.pipeline_outputs has mismatched core_format "
                        f"for {output}"
                    )
                if item.get("artifact_type") not in {
                    "full_config",
                    "full_config_alias",
                }:
                    errors.append(
                        f"{prefix}.pipeline_outputs has missing artifact_type "
                        f"for {output}"
                    )

        status = entry.get("status")
        if status == "stable" and not pipeline_outputs:
            errors.append(f"{prefix} stable core must list pipeline outputs")

    forbidden = data.get("forbidden_pipeline_outputs_until_generated", [])
    if not isinstance(forbidden, list):
        errors.append("forbidden_pipeline_outputs_until_generated must be a list")
    else:
        for output in forbidden:
            if isinstance(output, str) and output in outputs:
                errors.append(
                    "forbidden pipeline output appears in output_matrix before "
                    f"implementation is complete: {output}"
                )

    if "xray" not in seen_cores:
        errors.append("core compatibility report must explicitly state Xray status")

    return errors


def main() -> None:
    errors = validate_core_compatibility()
    if errors:
        print("ERROR: core compatibility validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK: core compatibility report validated.")


if __name__ == "__main__":
    main()
