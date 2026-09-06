# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_runtime_versions


LINKER_FLAG = "-checklinkname=0"
UPSTREAM_FIX = "a33349366d899068145f2d0e3ea0f5b2632fa3f2"


def _write_fixture(
    root: Path,
    *,
    go_toolchain: str = "1.26.8",
    go_ci: str | None = None,
    workflow_go: str = "1.26.8",
    linker_flag: str = LINKER_FLAG,
) -> None:
    (root / "config").mkdir()
    (root / ".github/workflows").mkdir(parents=True)
    (root / "src/go/tester").mkdir(parents=True)
    (root / "scripts").mkdir()
    go_payload = {
        "language": "1.24.0",
        "toolchain": go_toolchain,
        "container": go_toolchain,
        "container_variant": "alpine3.24",
    }
    if go_ci is not None:
        go_payload["ci"] = go_ci
    (root / "config/runtime-versions.json").write_text(
        json.dumps(
            {
                "python": {
                    "minimum": "3.10",
                    "container": "3.12.14",
                    "container_variant": "slim-bookworm",
                },
                "node": {
                    "minimum_major": 24,
                    "container": "24.20.0",
                    "container_variant": "bookworm-slim",
                    "ci": "24",
                },
                "go": go_payload,
                "sing_box": {
                    "release_validator": "1.13.18",
                    "embedded_tester": "1.9.7",
                    "embedded_linker_compat": {
                        "flag": linker_flag,
                        "scope": "legacy-tester-only",
                        "upstream_fix_commit": UPSTREAM_FIX,
                    },
                },
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
        f"FROM golang:{go_toolchain}-alpine3.24@sha256:deadbeef AS builder\n"
        f'RUN go build -ldflags="-s -w {linker_flag}" ./...\n'
        "FROM node:24.20.0-bookworm-slim@sha256:deadbeef AS node-runtime\n"
        "FROM python:3.12.14-slim-bookworm@sha256:deadbeef\n",
        encoding="utf-8",
    )
    (root / ".github/workflows/ci.yml").write_text(
        f"go-version: '{workflow_go}'\n"
        "node-version: '24'\n"
        "SING_BOX_VERSION: '1.13.18'\n"
        + "\n".join(f'run: go test -ldflags="{linker_flag}" ./...' for _ in range(4))
        + "\n",
        encoding="utf-8",
    )
    (root / "scripts/build_wasm.sh").write_text(
        f'go build -ldflags="{linker_flag}" ./...\n', encoding="utf-8"
    )
    (root / "src/go/tester/go.mod").write_text(
        f"module example\n\ngo 1.24.0\n\ntoolchain go{go_toolchain}\n"
        "\nrequire github.com/sagernet/sing-box v1.9.7\n",
        encoding="utf-8",
    )


def test_repository_runtime_versions_are_consistent() -> None:
    errors = validate_runtime_versions.validate_repository(Path("."))
    assert errors == []


def test_validator_detects_go_toolchain_drift(tmp_path: Path) -> None:
    _write_fixture(tmp_path, go_toolchain="1.26.7", workflow_go="1.26.7")
    manifest = json.loads(
        (tmp_path / "config/runtime-versions.json").read_text(encoding="utf-8")
    )
    manifest["go"]["toolchain"] = "1.26.8"
    (tmp_path / "config/runtime-versions.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert any("go.mod toolchain" in error for error in errors)


def test_validator_prefers_explicit_go_ci_over_toolchain(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        go_toolchain="1.26.8",
        go_ci="1.27.1",
        workflow_go="1.27.1",
    )

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert not any("go-version" in error for error in errors), errors
    assert any("must be identical" in error for error in errors), errors


def test_validator_rejects_any_stale_workflow_go_version(tmp_path: Path) -> None:
    _write_fixture(tmp_path, go_ci="1.26.8", workflow_go="1.26.8")
    (tmp_path / ".github/workflows/other.yml").write_text(
        "go-version: '1.23'\n", encoding="utf-8"
    )

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert any("other.yml go-version '1.23'" in error for error in errors)


def test_validator_rejects_minor_only_container_pin(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    manifest = json.loads(
        (tmp_path / "config/runtime-versions.json").read_text(encoding="utf-8")
    )
    manifest["python"]["container"] = "3.12"
    (tmp_path / "config/runtime-versions.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert any(
        "python.container must pin an exact patch release" in error for error in errors
    )


def test_validator_rejects_missing_legacy_linker_compat(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    (tmp_path / "scripts/build_wasm.sh").write_text(
        "go build ./...\n", encoding="utf-8"
    )

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert any("WASM legacy tester build" in error for error in errors)


def test_validator_rejects_broadened_legacy_linker_scope(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    manifest_path = tmp_path / "config/runtime-versions.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sing_box"]["embedded_linker_compat"]["scope"] = "all-go-builds"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = validate_runtime_versions.validate_repository(tmp_path)

    assert any("legacy-tester-only" in error for error in errors)
