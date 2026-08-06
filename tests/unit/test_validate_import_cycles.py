# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts.validate_import_cycles import find_cycles


def test_detects_synthetic_cycle(tmp_path: Path):
    package = tmp_path / "demo"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "a.py").write_text("from demo import b\n", encoding="utf-8")
    (package / "b.py").write_text("from demo import a\n", encoding="utf-8")
    assert find_cycles(package) == [("demo.a", "demo.b")]


def test_repository_has_no_first_party_cycles():
    root = Path(__file__).resolve().parents[2] / "src" / "configstream"
    assert find_cycles(root) == []
