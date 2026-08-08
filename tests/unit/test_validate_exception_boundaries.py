# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from scripts import validate_exception_boundaries as validator


def test_budget_detects_new_unreviewed_boundary(tmp_path, monkeypatch):
    src = tmp_path / "src" / "configstream"
    scripts = tmp_path / "scripts"
    src.mkdir(parents=True)
    scripts.mkdir()
    (src / "module.py").write_text(
        "try:\n    value = 1\nexcept Exception:\n    value = 0\n",
        encoding="utf-8",
    )
    budget = tmp_path / "budget.json"
    budget.write_text(
        json.dumps({"total_ceiling": 0, "path_ceilings": {}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "SCAN_ROOTS", (src, scripts))
    monkeypatch.setattr(validator, "BUDGET", budget)
    errors = validator.validate()
    assert any("unreviewed" in error for error in errors)


def test_repository_exception_budget_is_exact():
    assert validator.validate() == []
