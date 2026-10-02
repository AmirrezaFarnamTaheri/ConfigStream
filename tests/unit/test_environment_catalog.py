# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_environment_catalog


def test_generated_environment_catalog_is_current() -> None:
    assert generate_environment_catalog.generate(Path("."), check=True) == []


def test_catalog_contains_direct_and_settings_environment_variables() -> None:
    payload = json.loads(
        Path("docs/generated/environment-variables.json").read_text(encoding="utf-8")
    )
    variables = {item["name"]: item for item in payload["variables"]}
    assert "FETCH_TIMEOUT" in variables
    assert variables["FETCH_TIMEOUT"]["declared_in_settings"] is True
    assert "CS_SIGNING_PRIVATE_KEY_HEX" in variables
    assert variables["CS_SIGNING_PRIVATE_KEY_HEX"]["sensitive"] is True
    assert variables["CS_SIGNING_PRIVATE_KEY_HEX"]["default"] is None
    assert "GITHUB_SHA" in variables


def test_check_mode_reports_non_object_json_as_stale(tmp_path: Path) -> None:
    config_dir = tmp_path / "src/configstream"
    config_dir.mkdir(parents=True)
    (config_dir / "config.py").write_text(
        "class AppSettings:\n    FETCH_TIMEOUT: int = 15\n",
        encoding="utf-8",
    )
    generated = tmp_path / "docs/generated"
    generated.mkdir(parents=True)
    (generated / "environment-variables.json").write_text("[]\n", encoding="utf-8")
    (generated / "environment-variables.md").write_text("", encoding="utf-8")

    errors = generate_environment_catalog.generate(tmp_path, check=True)

    assert errors
    assert "source_digest current=None" in errors[0]
