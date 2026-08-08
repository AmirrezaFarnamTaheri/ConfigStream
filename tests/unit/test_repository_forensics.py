# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path

from scripts import collect_repository_forensics


def test_repository_forensics_is_current_and_secret_clean() -> None:
    assert collect_repository_forensics.generate(Path("."), check=True) == []


def test_repository_forensics_does_not_claim_upstream_history() -> None:
    payload = json.loads(
        Path("docs/generated/repository-forensics.json").read_text(encoding="utf-8")
    )
    assert payload["source"]["source_kind"] == "archive-snapshot"
    assert payload["remediation_checkout"]["history_origin"].startswith(
        "local baseline"
    )
    assert "upstream_commit_history" in payload["unavailable_claims"]
