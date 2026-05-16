# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prepare a list of release assets based on the output matrix."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List


def get_release_assets(output_dir: str, matrix_file: str) -> List[str]:
    """Return existing release asset paths declared by the output matrix."""
    matrix_path = Path(matrix_file)
    if not matrix_path.exists():
        raise FileNotFoundError(f"Required output matrix not found: {matrix_file}")

    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))

    output_path = Path(output_dir)
    assets: List[str] = []
    for entry in matrix.get("outputs", []):
        # Only include major subscription formats for the GitHub Release assets
        # to keep the release clean, while Pages hosts the full matrix.
        if entry.get("category") == "subscription" and entry.get("family") in {
            "universal",
            "singbox",
            "clash",
            "singbox-vpn",
        }:
            path = entry.get("path")
            if isinstance(path, str) and (output_path / path).exists():
                assets.append(path)

    return assets


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--matrix", default="docs/output_matrix.json")
    args = parser.parse_args()

    assets = get_release_assets(args.output_dir, args.matrix)
    # Print as a space-separated list for GitHub Actions
    print(" ".join([os.path.join(args.output_dir, a) for a in assets]))
