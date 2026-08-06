# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for the local Pages deployment fixture."""

from __future__ import annotations

from scripts.deploy_artifact_smoke import (
    _copy_frontend,
    _runtime_env,
    _write_output_fixture,
)
from scripts.validate_frontend_placeholders import (
    inject_frontend_keys,
    validate_frontend_placeholders,
)
from scripts.validate_pages_artifact import (
    validate_pages_artifact,
    write_pages_contract,
)


def test_deploy_fixture_satisfies_the_same_contract_as_pages(tmp_path) -> None:
    _copy_frontend(tmp_path)
    _write_output_fixture(tmp_path)
    inject_frontend_keys(tmp_path, _runtime_env())

    assert validate_frontend_placeholders(tmp_path, strict=True) == []
    write_pages_contract(tmp_path)
    assert validate_pages_artifact(tmp_path) == []
