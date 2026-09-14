#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Refresh tracked supply-chain evidence on a same-repo Dependabot branch.

This is designed for a ``workflow_run`` job that executes trusted code from the
default branch. It never executes files from the dependency-update branch: only
manifest/lock data is copied into a temporary tree and fed to the trusted
evidence generator. The resulting generated files are committed atomically via
the Git data API if the Dependabot ref still points at the expected head SHA.
"""

from __future__ import annotations

import argparse
import json
import sys
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from scripts.generate_supply_chain_evidence import generate

OUTPUT_PATHS = (
    "docs/generated/sbom.cdx.json",
    "docs/generated/dependency-licenses.json",
    "docs/generated/dependency-licenses.md",
)
FIXED_INPUT_PATHS = (
    "pyproject.toml",
    "requirements-prod.txt",
    "package-lock.json",
    "src/rust/ss_checker/Cargo.toml",
)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class GitHubApi:
    def __init__(self, token: str, repository: str, api_url: str) -> None:
        self.token = token
        self.repository = repository
        self.api_url = api_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        accept: str = "application/vnd.github+json",
    ) -> bytes:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.api_url}{path}",
            data=body,
            method=method,
            headers={
                "Accept": accept,
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "configstream-dependabot-evidence-refresh",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            with urlopen(request, timeout=30) as response:  # nosec B310
                return response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(
                f"GitHub API {method} {path} failed with {exc.code}: {detail}"
            ) from exc

    def json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw = self.request(method, path, payload=payload)
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise RuntimeError(f"GitHub API {method} {path} returned non-object JSON")
        return parsed

    def raw_file(self, path: str, ref: str) -> bytes:
        encoded = quote(path, safe="/")
        return self.request(
            "GET",
            f"/repos/{self.repository}/contents/{encoded}?ref={quote(ref, safe='')}",
            accept="application/vnd.github.raw+json",
        )


def _validated_context(
    repository: str, head_branch: str, head_sha: str
) -> tuple[str, str, str]:
    if not _REPO_RE.fullmatch(repository):
        raise ValueError(f"invalid repository: {repository!r}")
    if not head_branch.startswith("dependabot/") or ".." in head_branch:
        raise ValueError("refusing non-Dependabot branch")
    if not _SHA_RE.fullmatch(head_sha):
        raise ValueError("invalid Dependabot head SHA")
    return repository, head_branch, head_sha


def _ref_path(repository: str, branch: str) -> str:
    return f"/repos/{repository}/git/ref/heads/{quote(branch, safe='/')}"


def _current_ref_sha(api: GitHubApi, branch: str) -> str:
    payload = api.json("GET", _ref_path(api.repository, branch))
    obj = payload.get("object")
    if not isinstance(obj, dict) or not isinstance(obj.get("sha"), str):
        raise RuntimeError("branch ref response is missing object.sha")
    return str(obj["sha"])


def _tree_paths(api: GitHubApi, head_sha: str) -> tuple[str, list[str]]:
    commit = api.json(
        "GET", f"/repos/{api.repository}/git/commits/{quote(head_sha, safe='')}"
    )
    tree = commit.get("tree")
    if not isinstance(tree, dict) or not isinstance(tree.get("sha"), str):
        raise RuntimeError("commit response is missing tree.sha")
    tree_sha = str(tree["sha"])
    listing = api.json(
        "GET", f"/repos/{api.repository}/git/trees/{tree_sha}?recursive=1"
    )
    raw_entries = listing.get("tree")
    if not isinstance(raw_entries, list):
        raise RuntimeError("recursive tree response is missing tree entries")
    paths = [
        str(item["path"])
        for item in raw_entries
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    return tree_sha, paths


def _input_paths(tree_paths: list[str]) -> list[str]:
    go_mod_paths = sorted(
        path
        for path in tree_paths
        if path.startswith("src/go/")
        and path.endswith("/go.mod")
        and path.count("/") == 3
    )
    return [*FIXED_INPUT_PATHS, *go_mod_paths]


def _render_evidence(api: GitHubApi, head_sha: str, tree_paths: list[str]) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="configstream-dependabot-evidence-") as tmp:
        root = Path(tmp)
        for relative in _input_paths(tree_paths):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(api.raw_file(relative, head_sha))
        generate(root, check=False)
        return {
            relative: (root / relative).read_text(encoding="utf-8")
            for relative in OUTPUT_PATHS
        }


def _outputs_are_current(
    api: GitHubApi, head_sha: str, rendered: dict[str, str]
) -> bool:
    for path, expected in rendered.items():
        try:
            current = api.raw_file(path, head_sha).decode("utf-8")
        except RuntimeError:
            return False
        if current != expected:
            return False
    return True


def _create_commit(
    api: GitHubApi,
    *,
    head_sha: str,
    base_tree_sha: str,
    rendered: dict[str, str],
) -> str:
    entries: list[dict[str, str]] = []
    for path, content in rendered.items():
        blob = api.json(
            "POST",
            f"/repos/{api.repository}/git/blobs",
            payload={"content": content, "encoding": "utf-8"},
        )
        blob_sha = blob.get("sha")
        if not isinstance(blob_sha, str):
            raise RuntimeError(f"blob creation for {path} returned no SHA")
        entries.append(
            {"path": path, "mode": "100644", "type": "blob", "sha": blob_sha}
        )
    tree = api.json(
        "POST",
        f"/repos/{api.repository}/git/trees",
        payload={"base_tree": base_tree_sha, "tree": entries},
    )
    new_tree_sha = tree.get("sha")
    if not isinstance(new_tree_sha, str):
        raise RuntimeError("tree creation returned no SHA")
    commit = api.json(
        "POST",
        f"/repos/{api.repository}/git/commits",
        payload={
            "message": "chore(deps): refresh supply-chain evidence",
            "tree": new_tree_sha,
            "parents": [head_sha],
        },
    )
    commit_sha = commit.get("sha")
    if not isinstance(commit_sha, str):
        raise RuntimeError("commit creation returned no SHA")
    return commit_sha


def refresh(
    api: GitHubApi,
    *,
    repository: str,
    head_branch: str,
    head_sha: str,
) -> str | None:
    _validated_context(repository, head_branch, head_sha)
    if repository != api.repository:
        raise ValueError("repository context does not match API target")
    if _current_ref_sha(api, head_branch) != head_sha:
        raise RuntimeError("Dependabot branch moved before evidence refresh")
    base_tree_sha, tree_paths = _tree_paths(api, head_sha)
    rendered = _render_evidence(api, head_sha, tree_paths)
    if _outputs_are_current(api, head_sha, rendered):
        print("Supply-chain evidence is already current; nothing to commit.")
        return None
    commit_sha = _create_commit(
        api, head_sha=head_sha, base_tree_sha=base_tree_sha, rendered=rendered
    )
    if _current_ref_sha(api, head_branch) != head_sha:
        raise RuntimeError("Dependabot branch moved while evidence was generated")
    api.json(
        "PATCH",
        _ref_path(repository, head_branch),
        payload={"sha": commit_sha, "force": False},
    )
    print(f"Updated {head_branch} with supply-chain evidence commit {commit_sha}.")
    return commit_sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--head-branch", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--api-url", default="https://api.github.com")
    parser.add_argument(
        "--token-stdin", action="store_true", help="read the GitHub token from stdin"
    )
    args = parser.parse_args(argv)
    if not args.token_stdin:
        raise SystemExit("--token-stdin is required")
    token = sys.stdin.read().strip()
    if not token:
        raise SystemExit("GitHub token stdin is empty")
    api = GitHubApi(token, args.repository, args.api_url)
    refresh(
        api,
        repository=args.repository,
        head_branch=args.head_branch,
        head_sha=args.head_sha,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
