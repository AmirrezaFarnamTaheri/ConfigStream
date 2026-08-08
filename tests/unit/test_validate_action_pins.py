# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for immutable GitHub Action reference enforcement."""

from __future__ import annotations

from pathlib import Path

from scripts.validate_action_pins import validate_action_pins


def _workflow(root: Path, uses_line: str) -> Path:
    path = root / "workflow.yml"
    path.write_text(
        "name: test\non: push\njobs:\n  check:\n    runs-on: ubuntu-latest\n"
        f"    steps:\n      - uses: {uses_line}\n",
        encoding="utf-8",
    )
    return path


def test_rejects_mutable_tag(tmp_path: Path) -> None:
    _workflow(tmp_path, "actions/checkout@v7")
    result = validate_action_pins(tmp_path, manifest_path=None)
    assert result.errors
    assert "full commit SHA" in result.errors[0]


def test_rejects_sha_without_readable_version_comment(tmp_path: Path) -> None:
    _workflow(tmp_path, "actions/checkout@" + "a" * 40)
    result = validate_action_pins(tmp_path, manifest_path=None)
    assert any("version comment" in error for error in result.errors)


def test_accepts_sha_with_version_comment(tmp_path: Path) -> None:
    _workflow(tmp_path, "actions/checkout@" + "a" * 40 + " # v7")
    result = validate_action_pins(tmp_path, manifest_path=None)
    assert result.errors == []
    assert result.external_references == 1
    assert result.sha_pinned == 1


def test_ignores_local_and_digest_pinned_container_actions(tmp_path: Path) -> None:
    (tmp_path / "workflow.yml").write_text(
        "name: test\non: push\njobs:\n  check:\n    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: ./local-action\n"
        "      - uses: docker://alpine@sha256:" + "b" * 64 + "\n",
        encoding="utf-8",
    )
    result = validate_action_pins(tmp_path, manifest_path=None)
    assert result.errors == []
    assert result.external_references == 0


def test_rejects_sha_that_is_not_verified_for_declared_version(tmp_path: Path) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    _workflow(workflow_dir, "actions/checkout@" + "a" * 40 + " # v7")
    manifest = tmp_path / "pins.json"
    manifest.write_text(
        '{"schema_version":1,"entries":[{"action":"actions/checkout",'
        '"version":"v7","commit_sha":"' + "b" * 40 + '"}]}\n',
        encoding="utf-8",
    )
    result = validate_action_pins(workflow_dir, manifest_path=manifest)
    assert any("uses unverified SHA" in error for error in result.errors)


def test_repository_workflows_match_verified_tag_commits() -> None:
    result = validate_action_pins()
    assert result.errors == []
    assert result.external_references == result.sha_pinned
