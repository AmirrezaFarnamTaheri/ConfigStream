# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from scripts.validate_release_controls import validate


def test_required_release_controls_are_preserved() -> None:
    assert validate(Path(".")) == []


def test_release_controls_cover_optional_signing_and_safe_bootstrap() -> None:
    deploy = Path(".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")

    assert "VARIABLE_ALLOW_UNSIGNED_PAGES: ${{ vars.ALLOW_UNSIGNED_PAGES }}" in deploy
    assert "Resolve Pages unsigned trust policy" in deploy
    assert "config/pages-trust-policy.json" in deploy
    assert "bound_repository == repository and committed_allow" in deploy
    assert "snapshot_args+=(--allow-unsigned)" in deploy
    assert 'payload.get("failure_kind") == "missing_manifest"' in deploy
    assert "Automatic first-deployment bootstrap approved" in deploy
    assert deploy.count("verify_args+=(--allow-unsigned)") >= 2
