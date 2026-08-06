# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for canonical source path exclusions."""

from pathlib import Path

from scripts import validate_workflows


def _workflow_with_ignored_path(pattern: str) -> dict[str, object]:
    return {"on": {"push": {"paths-ignore": [pattern]}}}


def test_canonical_source_discovery_includes_middle_batches() -> None:
    sources = set(validate_workflows._canonical_source_paths())

    assert Path("sources/batch_2.txt") in sources
    assert Path("sources/batch_16.txt") in sources
    assert Path("sources/batch_17.txt") in sources


def test_ci_cannot_ignore_single_middle_canonical_batch() -> None:
    workflow = _workflow_with_ignored_path("sources/batch_2.txt")

    assert validate_workflows._ci_ignores_canonical_sources(workflow)


def test_ci_cannot_ignore_canonical_batch_range() -> None:
    workflow = _workflow_with_ignored_path("sources/batch_[2-9].txt")

    assert validate_workflows._ci_ignores_canonical_sources(workflow)


def test_ci_may_ignore_dynamic_source_backups() -> None:
    workflow = _workflow_with_ignored_path("sources/backup_dynamic/**")

    assert not validate_workflows._ci_ignores_canonical_sources(workflow)
