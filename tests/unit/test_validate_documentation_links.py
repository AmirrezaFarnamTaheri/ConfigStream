# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts.validate_documentation_links import validate


def test_repository_documentation_links_are_valid() -> None:
    assert validate(Path(".")) == []


def test_missing_local_link_is_reported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("[missing](docs/nope.md)\n", encoding="utf-8")

    errors = validate(tmp_path)

    assert errors == ["README.md:1: missing local link target docs/nope.md"]


def test_external_and_anchor_links_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "[external](https://example.com) [section](#section)\n", encoding="utf-8"
    )

    assert validate(tmp_path) == []
