# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import pytest

from configstream.constants import ARTIFACT_TRANSIENT_SUFFIXES
from configstream.output_logic import write_public_artifact_contract
from scripts import finalize_release_outputs, refresh_shard_contract, release_gate

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_public_manifest_excludes_all_canonical_transients(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CS_SIGNING_PRIVATE_KEY_HEX", raising=False)
    (tmp_path / "metadata.json").write_text(
        json.dumps({"total_working": 1, "total_tested": 1}), encoding="utf-8"
    )
    (tmp_path / "stable.txt").write_text("stable", encoding="utf-8")
    for suffix in ARTIFACT_TRANSIENT_SUFFIXES:
        (tmp_path / f"ephemeral{suffix}").write_text("transient", encoding="utf-8")

    manifest = write_public_artifact_contract(tmp_path)
    paths = {str(item["path"]) for item in manifest["files"]}

    assert "stable.txt" in paths
    assert not any(path.endswith(ARTIFACT_TRANSIENT_SUFFIXES) for path in paths)


def test_release_cleanup_uses_one_canonical_transient_policy() -> None:
    assert finalize_release_outputs.TRANSIENT_SUFFIXES is ARTIFACT_TRANSIENT_SUFFIXES
    assert refresh_shard_contract.TRANSIENT_SUFFIXES is ARTIFACT_TRANSIENT_SUFFIXES
    assert release_gate.TRANSIENT_SUFFIXES is ARTIFACT_TRANSIENT_SUFFIXES


def test_release_singbox_target_follows_runtime_manifest() -> None:
    runtime_manifest = REPO_ROOT / "config" / "runtime-versions.json"
    payload = json.loads(runtime_manifest.read_text(encoding="utf-8"))

    assert (
        finalize_release_outputs._release_singbox_version()
        == payload["sing_box"]["release_validator"]
    )
