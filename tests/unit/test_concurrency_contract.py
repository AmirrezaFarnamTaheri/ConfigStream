# SPDX-License-Identifier: AGPL-3.0-or-later
"""Static checks for pipeline test-concurrency ownership."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_pipeline_does_not_keep_unused_test_budget_semaphore() -> None:
    assert "test_budget" not in _read("src/configstream/pipeline/core.py")
    assert "test_budget" not in _read("src/configstream/pipeline/consumer.py")


def test_processing_consumer_uses_concurrency_manager_for_python_tests() -> None:
    consumer = _read("src/configstream/pipeline/consumer.py")

    assert "sem = concurrency.get_semaphore()" in consumer
    assert "async with sem:" in consumer
