# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
from scripts.validate_release_controls import validate


def test_required_release_controls_are_preserved() -> None:
    assert validate(Path(".")) == []



def test_release_controls_cover_optional_signing_and_safe_bootstrap() -> None:
    deploy = Path(".github/workflows/deploy-pages.yml").read_text(encoding="utf-8")

    assert deploy.count(
        "ALLOW_UNSIGNED_PAGES: ${{ vars.ALLOW_UNSIGNED_PAGES || 'true' }}"
    ) >= 4
    assert "snapshot source returned HTTP 404: .*artifact_manifest\\.json" in deploy
    assert (
        '[ "${LKG_MISSING:-false}" = true ] && '
        '[ "${DEPLOY_READY:-false}" = true ]'
    ) in deploy
