#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Upload ConfigStream artifacts to Hugging Face with optional Git LFS sync."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import Iterable

from huggingface_hub import HfApi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_LFS_PATTERNS = (
    "*.wasm",
    "*.zip",
    "*.db",
    "*.mmdb",
    "*.tar.gz",
    "*.AppImage",
    "*.dmg",
    "*.exe",
)


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )  # nosec B603


def _repo_http_url(repo_id: str, repo_type: str) -> str:
    if repo_type == "dataset":
        return f"https://huggingface.co/datasets/{repo_id}"
    if repo_type == "space":
        return f"https://huggingface.co/spaces/{repo_id}"
    return f"https://huggingface.co/{repo_id}"


def _repo_auth_url(repo_id: str, repo_type: str, token: str) -> str:
    url = _repo_http_url(repo_id, repo_type)
    return url.replace("https://", f"https://user:{token}@")


def _ensure_repo(repo_id: str, repo_type: str, token: str) -> None:
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type=repo_type, exist_ok=True)


def _clean_repo_root(repo_dir: Path) -> None:
    for entry in repo_dir.iterdir():
        if entry.name == ".git":
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink(missing_ok=True)


def _copy_tree(src: Path, dst: Path) -> None:
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def _git_lfs_available() -> bool:
    try:
        _run(["git", "lfs", "version"])
        return True
    except Exception:
        return False


def _sync_with_git_lfs(
    local_dir: Path,
    repo_id: str,
    repo_type: str,
    token: str,
    commit_message: str,
    lfs_patterns: Iterable[str],
) -> str:
    with tempfile.TemporaryDirectory(prefix="configstream-hf-") as tmp:
        tmp_path = Path(tmp)
        repo_dir = tmp_path / "repo"
        clone_url = _repo_auth_url(repo_id, repo_type, token)

        logger.info("Cloning %s", _repo_http_url(repo_id, repo_type))
        _run(["git", "clone", "--depth", "1", clone_url, str(repo_dir)])
        _run(["git", "lfs", "install", "--local"], cwd=repo_dir)
        for pattern in lfs_patterns:
            _run(["git", "lfs", "track", pattern], cwd=repo_dir)

        _clean_repo_root(repo_dir)
        _copy_tree(local_dir, repo_dir)

        _run(["git", "add", "-A"], cwd=repo_dir)
        status = _run(["git", "status", "--porcelain"], cwd=repo_dir).stdout.strip()
        if not status:
            logger.info("No changes detected for Hugging Face mirror.")
            return _repo_http_url(repo_id, repo_type)

        _run(
            [
                "git",
                "-c",
                "user.name=configstream-bot",
                "-c",
                "user.email=configstream@users.noreply.github.com",
                "commit",
                "-m",
                commit_message,
            ],
            cwd=repo_dir,
        )
        _run(["git", "push", "origin", "HEAD"], cwd=repo_dir)
        return _repo_http_url(repo_id, repo_type)


def upload_to_hf(
    local_dir: str,
    repo_id: str,
    token: str,
    repo_type: str = "dataset",
    commit_message: str = "Update ConfigStream output",
    use_git_lfs: bool = True,
    lfs_patterns: Iterable[str] = DEFAULT_LFS_PATTERNS,
) -> None:
    local_path = Path(local_dir)
    if not local_path.exists():
        logger.error("Local directory not found: %s", local_path)
        return

    logger.info("Uploading %s to %s (%s)", local_path, repo_id, repo_type)
    _ensure_repo(repo_id=repo_id, repo_type=repo_type, token=token)

    if use_git_lfs and _git_lfs_available():
        try:
            url = _sync_with_git_lfs(
                local_dir=local_path,
                repo_id=repo_id,
                repo_type=repo_type,
                token=token,
                commit_message=commit_message,
                lfs_patterns=lfs_patterns,
            )
            logger.info("Git LFS mirror sync complete: %s", url)
            return
        except Exception as exc:
            logger.warning("Git LFS sync failed; falling back to API upload: %s", exc)

    api = HfApi(token=token)
    url = api.upload_folder(
        folder_path=str(local_path),
        repo_id=repo_id,
        repo_type=repo_type,
        commit_message=commit_message,
    )
    logger.info("Upload complete via API: %s", url)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload output to Hugging Face")
    parser.add_argument("--path", default="output", help="Path to output directory")
    parser.add_argument(
        "--repo-id", required=True, help="Hugging Face repo ID (e.g. user/dataset)"
    )
    parser.add_argument("--token", help="HF API token (or use HF_TOKEN env var)")
    parser.add_argument(
        "--repo-type",
        default="dataset",
        choices=["dataset", "model", "space"],
        help="Repository type",
    )
    parser.add_argument(
        "--no-git-lfs",
        action="store_true",
        help="Disable git-lfs sync and force API upload.",
    )
    args = parser.parse_args()

    token = args.token or os.environ.get("HF_TOKEN")
    if not token:
        logger.error("No Hugging Face token provided. Set HF_TOKEN or pass --token.")
        return 1

    upload_to_hf(
        local_dir=args.path,
        repo_id=args.repo_id,
        token=token,
        repo_type=args.repo_type,
        use_git_lfs=not args.no_git_lfs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
