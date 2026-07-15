# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prepare deterministic, validated GitHub Release asset paths."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

EXPLICIT_ASSETS = (
    "xray.json",
    "surge.conf",
    "loon.conf",
    "quantumult.conf",
    "sip008.json",
    "format_compatibility.json",
    "metadata.json",
    "health.json",
    "artifact_manifest.json",
)


def get_release_assets(output_dir: str, matrix_file: str) -> List[str]:
    matrix_path = Path(matrix_file)
    if not matrix_path.exists():
        raise FileNotFoundError(f"Required output matrix not found: {matrix_file}")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    output_path = Path(output_dir)
    assets: List[str] = []
    for entry in matrix.get("outputs", []):
        if entry.get("category") == "subscription" and entry.get("family") in {
            "universal",
            "singbox",
            "clash",
            "singbox-vpn",
        }:
            path = entry.get("path")
            if isinstance(path, str) and (output_path / path).is_file():
                assets.append(path)
    for path in EXPLICIT_ASSETS:
        if (output_path / path).is_file() and path not in assets:
            assets.append(path)
    return sorted(assets)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--matrix", default="docs/output_matrix.json")
    args = parser.parse_args()
    print(
        " ".join(
            os.path.join(args.output_dir, path)
            for path in get_release_assets(args.output_dir, args.matrix)
        )
    )
