# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_live_smoke_seals_built_tester_for_strict_trust() -> None:
    workflow = (
        REPOSITORY_ROOT / ".github" / "workflows" / "configstream-live-smoke.yml"
    ).read_text(encoding="utf-8")

    assert "CGO_ENABLED=0 go build" in workflow
    assert "sha256sum configstream-tester" in workflow
    assert "> configstream-tester.sha256" in workflow
    assert "chmod 0444 configstream-tester.sha256" in workflow
    assert "CONFIGSTREAM_TESTER_BIN=$PWD/configstream-tester" in workflow

    digest_index = workflow.index("sha256sum configstream-tester")
    env_index = workflow.index("CONFIGSTREAM_TESTER_BIN=$PWD/configstream-tester")
    assert digest_index < env_index
