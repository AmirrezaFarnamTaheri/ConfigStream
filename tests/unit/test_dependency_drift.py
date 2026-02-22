# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for dependency drift checks."""

from __future__ import annotations

from pathlib import Path

from scripts.check_dependency_drift import check_dependency_drift


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_dependency_drift_passes_with_aligned_pins(tmp_path: Path) -> None:
    pyproject = _write(
        tmp_path / "pyproject.toml",
        """
[project]
dependencies = [
  "httpx>=0.28.0",
  "aiohttp>=3.9.0",
  "psutil>=5.9.0; sys_platform != 'win32'",
]
""".strip(),
    )
    req_prod = _write(
        tmp_path / "requirements-prod.txt",
        """
httpx==0.28.1
aiohttp==3.13.2
psutil==7.2.1
""".strip(),
    )
    req_dev = _write(
        tmp_path / "requirements.txt",
        """
httpx==0.28.1
aiohttp==3.13.2
psutil==7.2.1
""".strip(),
    )

    errors = check_dependency_drift(
        pyproject_path=pyproject,
        requirements_prod_path=req_prod,
        requirements_dev_path=req_dev,
    )
    assert errors == []


def test_dependency_drift_detects_missing_and_low_pins(tmp_path: Path) -> None:
    pyproject = _write(
        tmp_path / "pyproject.toml",
        """
[project]
dependencies = [
  "httpx>=0.28.0",
  "aiohttp>=3.9.0",
]
""".strip(),
    )
    req_prod = _write(
        tmp_path / "requirements-prod.txt",
        """
httpx==0.27.0
""".strip(),
    )
    req_dev = _write(
        tmp_path / "requirements.txt",
        """
httpx==0.27.0
""".strip(),
    )

    errors = check_dependency_drift(
        pyproject_path=pyproject,
        requirements_prod_path=req_prod,
        requirements_dev_path=req_dev,
    )

    assert errors
    assert any("httpx" in e and "below pyproject minimum" in e for e in errors)
    assert any("aiohttp" in e and "missing pin" in e for e in errors)
