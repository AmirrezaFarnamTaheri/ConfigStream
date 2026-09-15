# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from typing import Any

from scripts import refresh_dependabot_supply_chain_evidence as refresh


class CommitApi:
    repository = "owner/repo"

    def __init__(self) -> None:
        self.commit_payload: dict[str, Any] | None = None

    def json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert method == "POST"
        if path.endswith("/git/blobs"):
            return {"sha": "a" * 40}
        if path.endswith("/git/trees"):
            return {"sha": "b" * 40}
        if path.endswith("/git/commits"):
            self.commit_payload = payload
            return {"sha": "c" * 40}
        raise AssertionError(path)


def test_generated_evidence_commit_skips_duplicate_automatic_pr_runs() -> None:
    api = CommitApi()

    commit = refresh._create_commit(
        api,
        head_sha="d" * 40,
        base_tree_sha="e" * 40,
        rendered={"docs/generated/sbom.cdx.json": "{}\n"},
    )

    assert commit == "c" * 40
    assert api.commit_payload is not None
    assert api.commit_payload["message"].endswith("[skip ci]")
    assert refresh.FOLLOWUP_WORKFLOWS == (
        "ci.yml",
        "main.yml",
        "dependency-security.yml",
    )
