# SPDX-License-Identifier: AGPL-3.0-or-later
"""Metadata export completeness tests."""

from __future__ import annotations

import ast
from pathlib import Path

from configstream.pipeline_stats import PipelineStats

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_LOGIC_PATH = REPO_ROOT / "src" / "configstream" / "output_logic.py"


def _extract_save_metadata_meta_keys() -> set[str]:
    source = OUTPUT_LOGIC_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "save_metadata":
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                if not any(
                    isinstance(target, ast.Name) and target.id == "meta"
                    for target in stmt.targets
                ):
                    continue
                if not isinstance(stmt.value, ast.Dict):
                    continue
                keys: set[str] = set()
                for key_node in stmt.value.keys:
                    if isinstance(key_node, ast.Constant) and isinstance(
                        key_node.value, str
                    ):
                        keys.add(key_node.value)
                return keys
    raise AssertionError("Failed to locate `meta = {...}` in save_metadata()")


def test_save_metadata_contains_all_pipeline_stats_fields() -> None:
    meta_keys = _extract_save_metadata_meta_keys()
    pipeline_stats_keys = set(PipelineStats().to_dict().keys())
    missing = pipeline_stats_keys.difference(meta_keys)
    assert not missing, (
        "save_metadata meta dict is missing PipelineStats fields: " f"{sorted(missing)}"
    )
