# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for repository hygiene and security guards."""

from __future__ import annotations

import subprocess
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_TOKEN_PATTERNS = (
    re.compile(r"(?:token|key|secret|auth|sub|id)=[a-zA-Z0-9_-]{16,}", re.I),
    re.compile(
        r"(?i)(?:^|/)"
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        r"(?:/|$|[?#])"
    ),
    re.compile(r"(?i)/sub/[a-z0-9_-]{24,}(?:/|$|[?#])"),
)


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
    """Ensure generated artifact mirrors and runtime state are not tracked by Git."""
    tracked = _tracked_files()

    forbidden_prefixes = (
        "invvest/",
        "Latest Outputs to investigate/",
        "output/",
        ".cocoindex_code/",
        ".codebase-memory/",
        "scratch_",
    )
    runtime_state_prefixes = ("data/", "src/data/")
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
        if any(
            f.startswith(p) or (p != "output/" and f"/{p}" in f)
            for p in forbidden_prefixes
        )
        or any(f.startswith(p) for p in runtime_state_prefixes)
        or Path(f).name in forbidden_exact
    ]

    assert (
        not forbidden_tracked
    ), f"Generated artifacts, runtime state, or local review state are being tracked: {forbidden_tracked[:10]}..."


def test_no_tokens_in_tracked_sources() -> None:
    """Ensure tracked source lists do not contain live-looking tokens."""
    tracked = _tracked_files()
    if not tracked:
        return

    source_files = [f for f in tracked if f.startswith("sources/")]

    leaks = []
    for rel_path in source_files:
        path = ROOT / rel_path
        if not path.is_file():
            continue

        content = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), 1):
            if any(pattern.search(line) for pattern in SOURCE_TOKEN_PATTERNS):
                leaks.append(f"{rel_path}:{line_no}")

    assert not leaks, f"Tokens found in tracked source files: {leaks[:10]}..."


def test_source_token_patterns_cover_case_and_opaque_subscription_paths() -> None:
    samples = (
        "https://example.test/path?AUTH=abcdefghijklmnop",
        "https://example.test/sub/dXNlcl82Nzg4MzMxMjQ5LDE3Njk1MzUzMTkBqGm3A1STd",
    )

    assert all(
        any(pattern.search(sample) for pattern in SOURCE_TOKEN_PATTERNS)
        for sample in samples
    )
