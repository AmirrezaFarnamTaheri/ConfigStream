# SPDX-License-Identifier: AGPL-3.0-or-later
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts import refresh_dependabot_supply_chain_evidence as refresh


def test_direct_script_entrypoint_can_import_repo_modules() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "refresh_dependabot_supply_chain_evidence.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--repository" in result.stdout


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


def test_dependency_evidence_surface_includes_inventory_inputs_and_outputs() -> None:
    assert refresh.OUTPUT_PATHS == (
        "docs/generated/sbom.cdx.json",
        "docs/generated/dependency-licenses.json",
        "docs/generated/dependency-licenses.md",
        "docs/generated/dependency-inventory.json",
        "docs/generated/dependency-inventory.md",
    )
    assert {
        ".github/dependabot.yml",
        "config/container-images.json",
        "package.json",
        "requirements-publish.txt",
    }.issubset(refresh.FIXED_INPUT_PATHS)


class RenderApi(refresh.GitHubApi):
    repository = "owner/repo"

    def __init__(self) -> None:
        self.requested: list[str] = []

    def raw_file(self, path: str, ref: str) -> bytes:
        assert ref == "a" * 40
        self.requested.append(path)
        return f"fixture:{path}\n".encode()


def test_render_evidence_runs_all_dependency_generators(monkeypatch) -> None:
    api = RenderApi()
    calls: list[str] = []

    def write_outputs(root: Path, paths: tuple[str, ...]) -> None:
        for relative in paths:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"generated:{relative}\n", encoding="utf-8")

    def fake_supply_chain(root: Path, *, check: bool = False) -> list[str]:
        assert not check
        calls.append("supply-chain")
        write_outputs(root, refresh.OUTPUT_PATHS[:3])
        return []

    def fake_inventory(root: Path, *, check: bool = False) -> list[str]:
        assert not check
        calls.append("inventory")
        write_outputs(root, refresh.OUTPUT_PATHS[3:])
        return []

    monkeypatch.setattr(refresh, "generate_supply_chain_evidence", fake_supply_chain)
    monkeypatch.setattr(refresh, "generate_dependency_inventory", fake_inventory)

    rendered = refresh._render_evidence(
        api,
        "a" * 40,
        ["src/go/tester/go.mod"],
    )

    assert calls == ["supply-chain", "inventory"]
    assert tuple(rendered) == refresh.OUTPUT_PATHS
    assert api.requested == [*refresh.FIXED_INPUT_PATHS, "src/go/tester/go.mod"]


class FakeApi(refresh.GitHubApi):
    repository = "owner/repo"

    def __init__(self) -> None:
        self.ref = "a" * 40
        self.patched: list[tuple[str, dict[str, Any]]] = []
        self.dispatched: list[tuple[str, dict[str, Any]]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        accept: str = "application/vnd.github+json",
    ) -> bytes:
        del accept
        if (
            method == "POST"
            and "/actions/workflows/" in path
            and path.endswith("/dispatches")
        ):
            assert payload is not None
            self.dispatched.append((path, payload))
            return b""
        raise AssertionError((method, path, payload))

    def json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if method == "GET" and "/git/refs/heads/" in path:
            return {"object": {"sha": self.ref}}
        if method == "PATCH":
            assert payload is not None
            self.ref = str(payload["sha"])
            self.patched.append((path, payload))
            return {"object": {"sha": self.ref}}
        raise AssertionError((method, path, payload))


class PatchRaceApi(FakeApi):
    def json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if method == "PATCH":
            self.ref = "d" * 40
            raise RuntimeError("non-fast-forward ref update")
        return super().json(method, path, payload=payload)


class PatchFailureApi(FakeApi):
    def json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if method == "PATCH":
            raise RuntimeError("ref update API failure")
        return super().json(method, path, payload=payload)


def _stub_evidence_generation(
    monkeypatch: pytest.MonkeyPatch,
    *,
    commit_factory: Any | None = None,
) -> None:
    monkeypatch.setattr(refresh, "_tree_paths", lambda _api, _sha: ("b" * 40, []))
    monkeypatch.setattr(
        refresh,
        "_render_evidence",
        lambda _api, _sha, _paths: {"docs/generated/sbom.cdx.json": "{}\n"},
    )
    monkeypatch.setattr(refresh, "_outputs_are_current", lambda *_args: False)
    monkeypatch.setattr(
        refresh,
        "_create_commit",
        commit_factory or (lambda *_args, **_kwargs: "c" * 40),
    )


def test_refresh_updates_ref_only_after_rendered_commit(monkeypatch) -> None:
    api = FakeApi()
    _stub_evidence_generation(monkeypatch)

    commit = refresh.refresh(
        api,
        repository="owner/repo",
        head_branch="dependabot/pip/anyio-4.15.1",
        head_sha="a" * 40,
    )

    assert commit == "c" * 40
    assert api.ref == "c" * 40
    assert api.patched[0][0] == (
        "/repos/owner/repo/git/refs/heads/dependabot/pip/anyio-4.15.1"
    )
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


def test_refresh_noops_when_branch_moved_before_run(monkeypatch) -> None:
    api = FakeApi()
    api.ref = "d" * 40

    def unexpected_tree_lookup(*_args: Any, **_kwargs: Any) -> tuple[str, list[str]]:
        raise AssertionError("stale run must stop before reading the old commit")

    monkeypatch.setattr(refresh, "_tree_paths", unexpected_tree_lookup)

    assert (
        refresh.refresh(
            api,
            repository="owner/repo",
            head_branch="dependabot/pip/certifi-2026.7.22",
            head_sha="a" * 40,
        )
        is None
    )
    assert not api.patched


def test_refresh_noops_when_branch_moves_during_generation(monkeypatch) -> None:
    api = FakeApi()

    def create_commit(*_args: Any, **_kwargs: Any) -> str:
        api.ref = "d" * 40
        return "c" * 40

    _stub_evidence_generation(monkeypatch, commit_factory=create_commit)

    assert (
        refresh.refresh(
            api,
            repository="owner/repo",
            head_branch="dependabot/pip/uvicorn-0.52.4",
            head_sha="a" * 40,
        )
        is None
    )
    assert not api.patched


def test_refresh_noops_when_branch_moves_during_ref_update(monkeypatch) -> None:
    api = PatchRaceApi()
    _stub_evidence_generation(monkeypatch)

    assert (
        refresh.refresh(
            api,
            repository="owner/repo",
            head_branch="dependabot/pip/python-dotenv-1.2.3",
            head_sha="a" * 40,
        )
        is None
    )
    assert api.ref == "d" * 40


def test_refresh_preserves_real_ref_update_failures(monkeypatch) -> None:
    api = PatchFailureApi()
    _stub_evidence_generation(monkeypatch)

    with pytest.raises(RuntimeError, match="ref update API failure"):
        refresh.refresh(
            api,
            repository="owner/repo",
            head_branch="dependabot/pip/anyio-4.15.1",
            head_sha="a" * 40,
        )


def test_dispatch_followup_checks_targets_dependabot_branch() -> None:
    api = FakeApi()
    branch = "dependabot/pip/anyio-4.15.1"

    refresh._dispatch_followup_checks(api, branch)

    assert api.dispatched == [
        (
            f"/repos/owner/repo/actions/workflows/{workflow}/dispatches",
            {"ref": branch},
        )
        for workflow in refresh.FOLLOWUP_WORKFLOWS
    ]
