# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for resolving the repository-bound Pages trust policy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pages_trust_policy import resolve_allow_unsigned_pages


def _policy(
    tmp_path: Path, *, repository: str = "owner/repo", allow: bool = True
) -> Path:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "repository": repository,
                "allow_unsigned_pages": allow,
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(
    ("repository", "committed", "override", "expected"),
    [
        ("owner/repo", True, None, True),
        ("owner/repo", False, None, False),
        ("fork/repo", True, None, False),
        ("fork/repo", False, "true", True),
        ("owner/repo", True, "false", False),
    ],
)
def test_resolves_override_and_repository_binding(
    tmp_path: Path,
    repository: str,
    committed: bool,
    override: str | None,
    expected: bool,
) -> None:
    policy = _policy(tmp_path, allow=committed)
    assert (
        resolve_allow_unsigned_pages(
            repository=repository, override=override, policy_path=policy
        )
        is expected
    )


def test_rejects_invalid_override(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be true, false, or unset"):
        resolve_allow_unsigned_pages(
            repository="owner/repo",
            override="yes",
            policy_path=_policy(tmp_path),
        )


def test_rejects_invalid_policy_schema(tmp_path: Path) -> None:
    path = _policy(tmp_path)
    path.write_text('{"schema_version": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported Pages trust policy schema"):
        resolve_allow_unsigned_pages(
            repository="owner/repo", override=None, policy_path=path
        )


@pytest.mark.parametrize("committed", [True, False])
def test_unsigned_publication_is_permitted_when_signing_is_not_configured(
    tmp_path: Path, committed: bool
) -> None:
    """Availability contract: no usable keypair means the committed fail-closed
    default must not stop the project from publishing."""

    assert (
        resolve_allow_unsigned_pages(
            repository="owner/repo",
            override=None,
            policy_path=_policy(tmp_path, allow=committed),
            signing_configured=False,
        )
        is True
    )


def test_explicit_override_still_wins_over_degraded_signing(tmp_path: Path) -> None:
    assert (
        resolve_allow_unsigned_pages(
            repository="owner/repo",
            override="false",
            policy_path=_policy(tmp_path, allow=True),
            signing_configured=False,
        )
        is False
    )


def test_repository_binding_still_applies_when_signing_is_configured(
    tmp_path: Path,
) -> None:
    assert (
        resolve_allow_unsigned_pages(
            repository="fork/repo",
            override=None,
            policy_path=_policy(tmp_path, allow=True),
            signing_configured=True,
        )
        is False
    )
