# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for repository hygiene and security guards."""

from __future__ import annotations

import subprocess
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {proc.stderr}")
    return proc.stdout.splitlines()


def test_no_tracked_generated_artifacts() -> None:
    """Ensure generated artifact mirrors are not tracked by Git."""
    tracked = _tracked_files()

    forbidden_prefixes = (
        "invvest/",
        "Latest Outputs to investigate/",
        "output/",
        ".cocoindex_code/",
        ".codebase-memory/",
        "scratch_",
    )
    forbidden_exact = (
        "all_pr_comments.txt",
        "all_tests_results.txt",
        "pr_full_output.txt",
        "test_results.txt",
        "pr_inline_comments.json",
        "pr_issue_comments.json",
        "pr_review_threads.json",
        "pr_reviews_full.json",
    )
    forbidden_tracked = [
        f
        for f in tracked
        if any(f.startswith(p) or f"/{p}" in f for p in forbidden_prefixes)
        or Path(f).name in forbidden_exact
    ]

    assert (
        not forbidden_tracked
    ), f"Generated artifacts or local review state are being tracked: {forbidden_tracked[:10]}..."


def test_no_tokens_in_tracked_sources() -> None:
    """Ensure tracked source lists do not contain live-looking tokens."""
    tracked = _tracked_files()
    if not tracked:
        return

    # Pattern for likely subscription tokens: ?token=..., /sub/..., etc.
    # We look for high-entropy strings or common token parameter names
    token_pattern = re.compile(r"(?:token|key|secret|auth|sub|id)=[a-zA-Z0-9]{16,}")

    source_files = [
        f
        for f in tracked
        if f.startswith("sources/") or f == "consolidated_sources.txt"
    ]

    leaks = []
    for rel_path in source_files:
        path = ROOT / rel_path
        if not path.is_file():
            continue

        content = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), 1):
            if token_pattern.search(line):
                leaks.append(f"{rel_path}:{line_no}")

    assert not leaks, f"Tokens found in tracked source files: {leaks[:10]}..."
