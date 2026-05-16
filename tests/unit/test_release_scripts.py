# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression checks for release/evidence helper scripts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script(module_name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / rel_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_urls(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def test_prepare_release_assets_uses_output_matrix_without_legacy_fallback(tmp_path):
    script = _load_script("prepare_release_assets", "scripts/prepare_release_assets.py")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "base64.txt").write_text("dmxlc3M6Ly8=", encoding="utf-8")
    (output_dir / "singbox.json").write_text("{}", encoding="utf-8")

    matrix = tmp_path / "output_matrix.json"
    matrix.write_text(
        json.dumps(
            {
                "outputs": [
                    {
                        "category": "subscription",
                        "family": "universal",
                        "path": "base64.txt",
                    },
                    {
                        "category": "subscription",
                        "family": "singbox",
                        "path": "singbox.json",
                    },
                    {
                        "category": "subscription",
                        "family": "clash",
                        "path": "missing.yaml",
                    },
                    {
                        "category": "api",
                        "family": "metadata",
                        "path": "metadata.json",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    assert script.get_release_assets(str(output_dir), str(matrix)) == [
        "base64.txt",
        "singbox.json",
    ]
    with pytest.raises(FileNotFoundError):
        script.get_release_assets(str(output_dir), str(tmp_path / "missing.json"))


def test_consolidated_sources_mirror_matches_canonical_batches() -> None:
    consolidated = _read_urls(REPO_ROOT / "consolidated_sources.txt")
    batch_urls: set[str] = set()
    batch_files = sorted((REPO_ROOT / "sources").glob("batch_*.txt"))

    assert len(batch_files) == 17
    for batch_file in batch_files:
        batch_urls.update(_read_urls(batch_file))

    assert consolidated == batch_urls


def test_generate_evidence_bundle_embeds_native_client_report(tmp_path) -> None:
    script = _load_script(
        "generate_evidence_bundle", "scripts/generate_evidence_bundle.py"
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "metadata.json").write_text(
        json.dumps({"total_working": 0, "total_proxies": 0}), encoding="utf-8"
    )
    (output_dir / "health.json").write_text("{}", encoding="utf-8")
    (output_dir / "artifact_manifest.json").write_text("{}", encoding="utf-8")
    native_report = tmp_path / "native_client_check_report.json"
    native_report.write_text(
        json.dumps({"summary": {"passed": 1, "failed": 0, "skipped": 2}}),
        encoding="utf-8",
    )
    evidence_dir = tmp_path / "evidence"

    script.generate_evidence_bundle(
        str(output_dir), str(evidence_dir), native_report=str(native_report)
    )

    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    readme = (evidence_dir / "README.md").read_text(encoding="utf-8")

    assert summary["native_client_check"]["summary"]["passed"] == 1
    assert (evidence_dir / "native_client_check_report.json").exists()
    assert "Native Client Checks" in readme
