# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

import pytest

from scripts import refresh_dependabot_supply_chain_evidence as refresh


def test_validated_context_rejects_non_dependabot_branch() -> None:
    with pytest.raises(ValueError, match="non-Dependabot"):
        refresh._validated_context("owner/repo", "feature/test", "a" * 40)


def test_input_paths_discovers_only_one_level_go_modules() -> None:
    paths = [
        "src/go/tester/go.mod",
        "src/go/utls_client/go.mod",
        "src/go/nested/example/go.mod",
        "src/go/tester/go.sum",
    ]
    assert refresh._input_paths(paths) == [
        *refresh.FIXED_INPUT_PATHS,
        "src/go/tester/go.mod",
        "src/go/utls_client/go.mod",
    ]


class FakeApi:
    repository = "owner/repo"

    def __init__(self) -> None:
        self.ref = "a" * 40
        self.patched: list[tuple[str, dict[str, object]]] = []

    def json(self, method: str, path: str, *, payload=None):
        if method == "GET" and "/git/ref/heads/" in path:
            return {"object": {"sha": self.ref}}
        if method == "PATCH":
            assert payload is not None
            self.ref = str(payload["sha"])
            self.patched.append((path, payload))
            return {"object": {"sha": self.ref}}
        raise AssertionError((method, path, payload))


def test_refresh_updates_ref_only_after_rendered_commit(monkeypatch) -> None:
    api = FakeApi()
    monkeypatch.setattr(refresh, "_tree_paths", lambda _api, _sha: ("b" * 40, []))
    monkeypatch.setattr(
        refresh,
        "_render_evidence",
        lambda _api, _sha, _paths: {"docs/generated/sbom.cdx.json": "{}\n"},
    )
    monkeypatch.setattr(refresh, "_outputs_are_current", lambda *_args: False)
    monkeypatch.setattr(refresh, "_create_commit", lambda *_args, **_kwargs: "c" * 40)

    commit = refresh.refresh(
        api,
        repository="owner/repo",
        head_branch="dependabot/pip/anyio-4.15.1",
        head_sha="a" * 40,
    )

    assert commit == "c" * 40
    assert api.ref == "c" * 40
    assert api.patched[0][1] == {"sha": "c" * 40, "force": False}


def test_refresh_noops_when_evidence_is_current(monkeypatch) -> None:
    api = FakeApi()
    monkeypatch.setattr(refresh, "_tree_paths", lambda _api, _sha: ("b" * 40, []))
    monkeypatch.setattr(refresh, "_render_evidence", lambda *_args: {})
    monkeypatch.setattr(refresh, "_outputs_are_current", lambda *_args: True)

    assert (
        refresh.refresh(
            api,
            repository="owner/repo",
            head_branch="dependabot/npm_and_yarn/vite-8.3.0",
            head_sha="a" * 40,
        )
        is None
    )
    assert not api.patched
