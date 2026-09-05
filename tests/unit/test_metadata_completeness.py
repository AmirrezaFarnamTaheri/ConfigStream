# SPDX-License-Identifier: AGPL-3.0-or-later
"""Metadata export completeness tests."""

from __future__ import annotations

import ast
from pathlib import Path

from configstream.pipeline_stats import PipelineStats

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_LOGIC_PATH = REPO_ROOT / "src" / "configstream" / "output" / "metadata.py"


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
    assert (
        not missing
    ), f"save_metadata meta dict is missing PipelineStats fields: {sorted(missing)}"


def test_public_metadata_preserves_zero_counts_and_snapshot(tmp_path: Path) -> None:
    import json
    from configstream.output.metadata import save_metadata, _json_snapshot_sha256
    from configstream.models import Proxy

    proxy = Proxy(
        config="socks5://1.1.1.1:1080",
        protocol="socks5",
        address="1.1.1.1",
        port=1080,
        is_working=True,
    )
    public: list[dict[str, object]] = []
    (tmp_path / "proxies.json").write_text(json.dumps(public), encoding="utf-8")
    save_metadata(
        {"public_record_count": 0, "public_working_count": 0}, [proxy], tmp_path
    )
    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["total_proxies"] == 0
    assert metadata["total_working"] == 0
    assert metadata["proxies_snapshot_hash"] == _json_snapshot_sha256(public)


def test_dict_metadata_preserves_explicit_zero_telemetry(tmp_path: Path) -> None:
    import json
    from configstream.output.metadata import save_metadata
    from configstream.models import Proxy

    proxy = Proxy(
        config="socks5://1.1.1.1:1080",
        protocol="socks5",
        address="1.1.1.1",
        port=1080,
        is_working=True,
    )
    save_metadata(
        {
            "fetched_lines": 0,
            "total_fetched": 99,
            "fetched_sources": 4,
            "total_configured_sources": 0,
            "washed_chains": 0,
            "washer_success_count": 7,
            "shielded_count": 3,
            "shielded_candidate_count": 0,
        },
        [proxy],
        tmp_path,
    )

    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["fetched_lines"] == 0
    assert metadata["total_lines_sourced"] == 0
    assert metadata["total_configured_sources"] == 0
    assert metadata["sources_count"] == 0
    assert metadata["washer_success_count"] == 0
    assert metadata["shielded_candidate_count"] == 0
