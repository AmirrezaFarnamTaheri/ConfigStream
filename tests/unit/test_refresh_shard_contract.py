# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.refresh_shard_contract import refresh_shard_contract


def test_refresh_shard_contract_prunes_transients_and_hashes_final_lineage(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output_batch_1_part_1"
    output.mkdir()
    (output / "metadata.json").write_text(
        json.dumps({"total_working": 1, "total_tested": 1}), encoding="utf-8"
    )
    lineage = output / "shard_lineage.json"
    lineage.write_text('{"status":"running"}\n', encoding="utf-8")
    (output / "pipeline_events.jsonl").write_text("before\n", encoding="utf-8")
    (output / "metadata.json.lock").write_text("transient", encoding="utf-8")

    refresh_shard_contract(output)
    lineage.write_text('{"status":"success"}\n', encoding="utf-8")
    (output / "pipeline_events.jsonl").write_text("before\nafter\n", encoding="utf-8")
    (output / "stale.lock").write_text("transient", encoding="utf-8")
    manifest = refresh_shard_contract(output)

    entries = {item["path"]: item for item in manifest["files"]}
    assert not (output / "metadata.json.lock").exists()
    assert not (output / "stale.lock").exists()
    assert all(not path.endswith(".lock") for path in entries)
    for rel_path in ("shard_lineage.json", "pipeline_events.jsonl"):
        path = output / rel_path
        assert entries[rel_path]["size_bytes"] == path.stat().st_size
        assert entries[rel_path]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
