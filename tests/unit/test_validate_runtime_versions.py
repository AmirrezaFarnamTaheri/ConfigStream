# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_runtime_versions


def test_repository_runtime_versions_are_consistent() -> None:
    errors = validate_runtime_versions.validate_repository(Path("."))
    assert errors == []


def test_validator_detects_go_toolchain_drift(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "src/go/tester").mkdir(parents=True)
    (tmp_path / "config/runtime-versions.json").write_text(
        json.dumps(
            {
                "python": {"minimum": "3.10", "container": "3.12"},
                "node": {"minimum_major": 24, "container": "24", "ci": "24"},
                "go": {
                    "language": "1.24.0",
                    "toolchain": "1.24.3",
                    "container": "1.24.3",
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.10"\n', encoding="utf-8"
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"engines": {"node": ">=24"}}), encoding="utf-8"
    )
    (tmp_path / "Dockerfile").write_text(
        "FROM golang:1.24.3-alpine AS builder\n"
        "FROM node:24-slim AS node-runtime\n"
        "FROM python:3.12-slim\n",
        encoding="utf-8",
    )
    (tmp_path / ".github/workflows/ci.yml").write_text(
        "go-version: '1.24.3'\nnode-version: '24'\n", encoding="utf-8"
    )
    (tmp_path / "src/go/tester/go.mod").write_text(
        "module example\n\ngo 1.24.0\n\ntoolchain go1.24.2\n",
        encoding="utf-8",
    )

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert any("go.mod toolchain" in error for error in errors)
