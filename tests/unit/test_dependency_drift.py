# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for dependency drift checks."""

from __future__ import annotations

from pathlib import Path

from scripts.check_dependency_drift import check_dependency_drift, check_publisher_pins


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
        tmp_path / "requirements-dev.txt",
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
        tmp_path / "requirements-dev.txt",
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


def test_dependency_drift_resolves_local_requirement_includes(tmp_path: Path) -> None:
    pyproject = _write(
        tmp_path / "pyproject.toml",
        '[project]\ndependencies = [\n  "httpx>=0.28.0",\n]\n',
    )
    req_prod = _write(tmp_path / "requirements-prod.txt", "httpx==0.28.1\n")
    req_dev = _write(
        tmp_path / "requirements-dev.txt",
        "-r requirements-prod.txt\npytest==9.1.1\n",
    )

    assert check_dependency_drift(
        pyproject_path=pyproject,
        requirements_prod_path=req_prod,
        requirements_dev_path=req_dev,
    ) == []


def test_dependency_drift_requires_optional_dev_dependency_pins(tmp_path: Path) -> None:
    pyproject = _write(
        tmp_path / "pyproject.toml",
        """
[project]
dependencies = ["httpx>=0.28.0"]

[project.optional-dependencies]
dev = ["bandit==1.8.6"]
""".strip(),
    )
    req_prod = _write(tmp_path / "requirements-prod.txt", "httpx==0.28.1\n")
    req_dev = _write(
        tmp_path / "requirements-dev.txt",
        "-r requirements-prod.txt\npytest==9.1.1\n",
    )

    errors = check_dependency_drift(
        pyproject_path=pyproject,
        requirements_prod_path=req_prod,
        requirements_dev_path=req_dev,
    )

    assert errors == [
        "requirements-dev.txt missing pin for optional dev dependency 'bandit'"
    ]


def test_dependency_drift_requires_exact_aligned_build_dependencies(tmp_path: Path) -> None:
    pyproject = _write(
        tmp_path / "pyproject.toml",
        """
[build-system]
requires = ["setuptools>=70", "wheel==0.47.0"]
build-backend = "setuptools.build_meta"

[project]
dependencies = ["httpx>=0.28.0"]
""".strip(),
    )
    req_prod = _write(tmp_path / "requirements-prod.txt", "httpx==0.28.1\n")
    req_dev = _write(
        tmp_path / "requirements-dev.txt",
        "-r requirements-prod.txt\nsetuptools==83.0.0\nwheel==0.46.0\n",
    )

    errors = check_dependency_drift(
        pyproject_path=pyproject,
        requirements_prod_path=req_prod,
        requirements_dev_path=req_dev,
    )

    assert any("setuptools" in error and "exact pin" in error for error in errors)
    assert any("wheel" in error and "must match" in error for error in errors)


def test_publisher_lock_owns_versions_without_checker_duplication(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "requirements-publish.txt",
        """
huggingface-hub==9.9.9
google-api-python-client==8.8.8
google-auth==7.7.7
""".strip(),
    )

    assert check_publisher_pins(path) == []


def test_publisher_lock_rejects_missing_unpinned_and_unreviewed_entries(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path / "requirements-publish.txt",
        """
huggingface-hub==1.0.0
google-auth>=2.0.0
extra-sdk==3.0.0
""".strip(),
    )

    errors = check_publisher_pins(path)

    assert any("google-api-python-client" in error for error in errors)
    assert any("google-auth" in error and "exact-pin" in error for error in errors)
    assert any("unreviewed packages: extra-sdk" in error for error in errors)
    assert any("non-exact dependency entries: google-auth>=2.0.0" in error for error in errors)
