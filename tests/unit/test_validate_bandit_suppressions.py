# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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


def test_validate_bandit_suppressions_accepts_active_explicit_rules(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "src/configstream/example.py",
        "import subprocess  # nosec B404\n",
    )
    rel_path = str(Path("src/configstream/example.py"))

    errors = validator.validate_bandit_suppressions(
        ("src/configstream",),
        active_findings={(rel_path, 1): {"B404"}},
    )

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


def test_validate_bandit_suppressions_rejects_stale_or_misplaced_rules(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "src/configstream/example.py",
        "import subprocess  # nosec B404\n",
    )

    errors = validator.validate_bandit_suppressions(
        ("src/configstream",),
        active_findings={},
    )

    assert len(errors) == 1
    assert "stale or misplaced nosec rule token" in errors[0]


def test_main_require_active_uses_active_bandit_findings(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "scripts/example.py",
        "import subprocess  # nosec B404\n",
    )
    rel_path = str(Path("scripts/example.py"))
    monkeypatch.setattr(
        validator,
        "_collect_active_bandit_findings",
        lambda scan_roots: {(rel_path, 1): {"B404"}},
    )

    assert validator.main(["--require-active", "scripts"]) == 0


def test_collect_active_findings_rejects_empty_report(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="No module named bandit",
        )

    monkeypatch.setattr(validator.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="empty JSON report") as error:
        validator._collect_active_bandit_findings(("scripts",))

    assert "No module named bandit" in str(error.value)


def test_collect_active_findings_requires_results_list(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()

    def fake_run(command, **kwargs):
        report_path = Path(command[command.index("-o") + 1])
        report_path.write_text('{"results": {}}', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(validator.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="results list"):
        validator._collect_active_bandit_findings(("scripts",))
