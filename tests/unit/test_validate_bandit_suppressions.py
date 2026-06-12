# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from scripts import validate_bandit_suppressions as validator


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_validate_bandit_suppressions_accepts_explicit_rules(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "src/configstream/example.py",
        "import subprocess  # nosec B404\n",
    )

    errors = validator.validate_bandit_suppressions(("src/configstream",))

    assert errors == []


def test_validate_bandit_suppressions_rejects_bare_nosec(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "scripts/example.py",
        "import subprocess  # nosec\n",
    )

    errors = validator.validate_bandit_suppressions(("scripts",))

    assert len(errors) == 1
    assert "bare Bandit suppression is forbidden" in errors[0]


def test_validate_bandit_suppressions_rejects_invalid_tokens(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "tools/example.py",
        "import subprocess  # nosec B404 reason\n",
    )

    errors = validator.validate_bandit_suppressions(("tools",))

    assert len(errors) == 1
    assert "invalid nosec rule token" in errors[0]


def test_validate_bandit_suppressions_rejects_duplicates(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "frontend/assets/js/example.js",
        "const value = 1; // # nosec B101,B101\n",
    )

    errors = validator.validate_bandit_suppressions(("frontend/assets/js",))

    assert len(errors) == 1
    assert "duplicate nosec rule token" in errors[0]
