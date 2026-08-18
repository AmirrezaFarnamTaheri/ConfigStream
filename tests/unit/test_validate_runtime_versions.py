# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_runtime_versions


def _write_fixture(
    root: Path,
    *,
    go_toolchain: str = "1.24.3",
    go_ci: str | None = None,
    workflow_go: str = "1.24.3",
) -> None:
    (root / "config").mkdir()
    (root / ".github/workflows").mkdir(parents=True)
    (root / "src/go/tester").mkdir(parents=True)
    go_payload = {
        "language": "1.24.0",
        "toolchain": go_toolchain,
        "container": "1.24",
    }
    if go_ci is not None:
        go_payload["ci"] = go_ci
    (root / "config/runtime-versions.json").write_text(
        json.dumps(
            {
                "python": {"minimum": "3.10", "container": "3.12"},
                "node": {"minimum_major": 24, "container": "24", "ci": "24"},
                "go": go_payload,
            }
        ),
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.10"\n', encoding="utf-8"
    )
    (root / "package.json").write_text(
        json.dumps({"engines": {"node": ">=24"}}), encoding="utf-8"
    )
    (root / "Dockerfile").write_text(
        "FROM golang:1.24-alpine@sha256:deadbeef AS builder\n"
        "FROM node:24-slim@sha256:deadbeef AS node-runtime\n"
        "FROM python:3.12-slim@sha256:deadbeef\n",
        encoding="utf-8",
    )
    (root / ".github/workflows/ci.yml").write_text(
        f"go-version: '{workflow_go}'\nnode-version: '24'\n", encoding="utf-8"
    )
    (root / "src/go/tester/go.mod").write_text(
        f"module example\n\ngo 1.24.0\n\ntoolchain go{go_toolchain}\n",
        encoding="utf-8",
    )


def test_repository_runtime_versions_are_consistent() -> None:
    errors = validate_runtime_versions.validate_repository(Path("."))
    assert errors == []


def test_validator_detects_go_toolchain_drift(tmp_path: Path) -> None:
    _write_fixture(tmp_path, go_toolchain="1.24.2", workflow_go="1.24.2")
    manifest = json.loads(
        (tmp_path / "config/runtime-versions.json").read_text(encoding="utf-8")
    )
    manifest["go"]["toolchain"] = "1.24.3"
    (tmp_path / "config/runtime-versions.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert any("go.mod toolchain" in error for error in errors)


def test_validator_prefers_explicit_go_ci_over_toolchain(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        go_toolchain="1.24.3",
        go_ci="1.24.4",
        workflow_go="1.24.4",
    )

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert not any("go-version" in error for error in errors), errors


def test_validator_rejects_any_stale_workflow_go_version(tmp_path: Path) -> None:
    _write_fixture(tmp_path, go_ci="1.24.3", workflow_go="1.24.3")
    (tmp_path / ".github/workflows/other.yml").write_text(
        "go-version: '1.23'\n", encoding="utf-8"
    )

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert any("other.yml go-version '1.23'" in error for error in errors)
