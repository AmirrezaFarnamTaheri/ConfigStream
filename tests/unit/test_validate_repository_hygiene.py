# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts.validate_repository_hygiene import (
    EXPECTED_BATCH_COUNT,
    validate,
    validate_source_layout,
)


def _write_source_layout(root: Path) -> None:
    source_dir = root / "sources"
    source_dir.mkdir(parents=True)
    urls: list[str] = []
    for index in range(1, EXPECTED_BATCH_COUNT + 1):
        url = f"https://example.test/source-{index}"
        urls.append(url)
        (source_dir / f"batch_{index}.txt").write_text(
            f"# batch {index}\n{url}\n", encoding="utf-8"
        )


def test_repository_has_no_generated_review_artifacts() -> None:
    assert validate(Path(".")) == []


def test_hygiene_rejects_agent_session_state(tmp_path: Path) -> None:
    _write_source_layout(tmp_path)
    (tmp_path / ".absolute-work").mkdir()

    errors = validate(tmp_path)

    assert errors == [
        "generated, redundant, or one-off artifact present: .absolute-work"
    ]


def test_hygiene_rejects_mock_path_debris(tmp_path: Path) -> None:
    _write_source_layout(tmp_path)
    (tmp_path / "MagicMock" / "EventStream").mkdir(parents=True)

    errors = validate(tmp_path)

    assert errors == [
        "generated, redundant, or one-off artifact present: MagicMock"
    ]


def test_hygiene_rejects_removed_consolidated_mirror(tmp_path: Path) -> None:
    _write_source_layout(tmp_path)
    (tmp_path / "consolidated_sources.txt").write_text(
        "https://example.test/extra\n", encoding="utf-8"
    )

    errors = validate(tmp_path)

    assert any("consolidated_sources.txt" in error for error in errors)


def test_source_layout_rejects_duplicate_urls_across_batches(tmp_path: Path) -> None:
    _write_source_layout(tmp_path)
    duplicate = "https://example.test/source-1"
    (tmp_path / "sources" / "batch_2.txt").write_text(
        f"# batch 2\n{duplicate}\n", encoding="utf-8"
    )
    errors = validate_source_layout(tmp_path)

    assert any("duplicate source URL" in error for error in errors)


def test_hygiene_rejects_top_level_review_artifact(tmp_path: Path) -> None:
    _write_source_layout(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "OLD_SECURITY_AUDIT.md").write_text("stale", encoding="utf-8")

    errors = validate(tmp_path)

    assert any("point-in-time review artifacts" in error for error in errors)


def test_hygiene_rejects_embedded_agent_plan_directory(tmp_path: Path) -> None:
    _write_source_layout(tmp_path)
    (tmp_path / "docs" / "superpowers" / "plans").mkdir(parents=True)

    errors = validate(tmp_path)

    assert any("docs/superpowers/plans" in error for error in errors)


def test_hygiene_rejects_binary_font_assets(tmp_path: Path) -> None:
    _write_source_layout(tmp_path)
    font = tmp_path / "frontend" / "assets" / "fonts" / "example.woff2"
    font.parent.mkdir(parents=True)
    font.write_bytes(b"font")

    errors = validate(tmp_path)

    assert any("binary font assets" in error for error in errors)


def test_hygiene_rejects_tracked_runtime_state(tmp_path: Path) -> None:
    import subprocess

    _write_source_layout(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    runtime = tmp_path / "data" / "test_cache.json"
    runtime.parent.mkdir()
    runtime.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "-f", "data/test_cache.json"], cwd=tmp_path, check=True)

    errors = validate(tmp_path)

    assert any("runtime state must remain ignored and untracked" in error for error in errors)
