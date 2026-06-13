# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from scripts import validate_test_skips as validator


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_validate_test_skips_accepts_current_repo_tests() -> None:
    assert validator.validate_test_skips(("tests",)) == []


def test_validate_test_skips_accepts_runtime_environment_skip(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "tests/test_frontend.py",
        """
import pytest


def test_frontend_fixture():
    if not ready:
        pytest.skip("Frontend directory not found")
""".lstrip(),
    )

    assert validator.validate_test_skips(("tests",)) == []


def test_validate_test_skips_accepts_environment_skipif(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "tests/test_browser.py",
        """
import pytest as pt

pytestmark = pt.mark.skipif(
    not playwright_ready,
    reason="Playwright browsers not installed",
)
""".lstrip(),
    )

    assert validator.validate_test_skips(("tests",)) == []


def test_validate_test_skips_accepts_imported_aliases(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "tests/test_alias.py",
        """
from pytest import mark, skip

pytestmark = mark.skipif(
    not node_ready,
    reason="node is required for frontend failover tests",
)


def test_node_fixture():
    skip("Loopback HTTP server is unavailable in this environment")
""".lstrip(),
    )

    assert validator.validate_test_skips(("tests",)) == []


def test_validate_test_skips_rejects_missing_reason(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "tests/test_missing_reason.py",
        """
import pytest


def test_skipped():
    pytest.skip()
""".lstrip(),
    )

    errors = validator.validate_test_skips(("tests",))

    assert len(errors) == 1
    assert "must include a literal reason" in errors[0]


def test_validate_test_skips_rejects_permanent_skip_marker(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "tests/test_permanent.py",
        """
import pytest


@pytest.mark.skip(reason="Playwright browsers not installed")
def test_never_runs():
    assert False
""".lstrip(),
    )

    errors = validator.validate_test_skips(("tests",))

    assert len(errors) == 1
    assert "permanent pytest.mark.skip is forbidden" in errors[0]


def test_validate_test_skips_rejects_constant_skipif(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "tests/test_constant.py",
        """
import pytest

pytestmark = pytest.mark.skipif(
    True,
    reason="Playwright browsers not installed",
)
""".lstrip(),
    )

    errors = validator.validate_test_skips(("tests",))

    assert len(errors) == 1
    assert "must not use a constant predicate" in errors[0]


def test_validate_test_skips_rejects_vague_reason(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "tests/test_vague.py",
        """
import pytest


def test_vague_skip():
    pytest.skip("TODO")
""".lstrip(),
    )

    errors = validator.validate_test_skips(("tests",))

    assert len(errors) == 3
    assert any("too short" in error for error in errors)
    assert any("deferred or disabled work" in error for error in errors)
    assert any("must identify the missing environment" in error for error in errors)


def test_main_accepts_valid_tmp_tree(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    _write(
        tmp_path / "tests/test_valid.py",
        """
import pytest

pytestmark = pytest.mark.skipif(
    not browser_ready,
    reason="Playwright browsers not installed",
)
""".lstrip(),
    )

    assert validator.main(["tests"]) == 0
