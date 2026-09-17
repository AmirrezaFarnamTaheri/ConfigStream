# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from scripts import validate_exception_boundaries as validator


def _configure(tmp_path, monkeypatch, source: str, ceiling: int) -> None:
    src = tmp_path / "src" / "configstream"
    scripts = tmp_path / "scripts"
    src.mkdir(parents=True)
    scripts.mkdir()
    (src / "module.py").write_text(source, encoding="utf-8")
    budget = tmp_path / "budget.json"
    budget.write_text(
        json.dumps(
            {
                "total_ceiling": ceiling,
                "path_ceilings": {"src/configstream/module.py": ceiling} if ceiling else {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "SCAN_ROOTS", (src, scripts))
    monkeypatch.setattr(validator, "BUDGET", budget)


def test_budget_detects_new_unreviewed_boundary(tmp_path, monkeypatch):
    _configure(
        tmp_path,
        monkeypatch,
        "try:\n    value = 1\nexcept Exception:\n    value = 0\n",
        0,
    )
    errors = validator.validate()
    assert any("unreviewed" in error for error in errors)


def test_silent_broad_pass_is_rejected(tmp_path, monkeypatch):
    _configure(
        tmp_path,
        monkeypatch,
        "try:\n    value = 1\nexcept Exception:\n    pass\n",
        1,
    )
    errors = validator.validate()
    assert errors == [
        "silent broad exception pass is forbidden: src/configstream/module.py:3"
    ]


def test_logged_broad_recovery_remains_budgeted(tmp_path, monkeypatch):
    _configure(
        tmp_path,
        monkeypatch,
        "import logging\ntry:\n    value = 1\nexcept Exception:\n    logging.getLogger(__name__).debug('fallback')\n    value = 0\n",
        1,
    )
    assert validator.validate() == []


def test_repository_exception_budget_is_exact():
    assert validator.validate() == []
