# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for the source-provider registry.

``assert_repository_allowed`` is the gate that keeps known-stale or
ownership-ambiguous mirrors out of production acquisition (it's called
directly from the GitHub blob adapter before any fetch). It had zero test
coverage, so a regression here -- e.g. a case-sensitivity slip, or the block
list silently no-op'ing -- would not be caught until a blocked source made
it back into a live pipeline run.
"""

import pytest

from configstream.sources.registry import (
    DATABAY,
    PROVIDERS,
    PROXIFLY,
    assert_repository_allowed,
    get_provider,
)


def test_known_providers_are_registered() -> None:
    assert PROVIDERS[DATABAY.provider_id] is DATABAY
    assert PROVIDERS[PROXIFLY.provider_id] is PROXIFLY


def test_get_provider_returns_registered_provider() -> None:
    assert get_provider("databay-free-proxy-list") is DATABAY


def test_get_provider_rejects_unknown_id() -> None:
    with pytest.raises(KeyError):
        get_provider("not-a-real-provider")


def test_assert_repository_allowed_permits_unlisted_repository() -> None:
    # Must not raise.
    assert_repository_allowed("databay-labs/free-proxy-list")


def test_assert_repository_allowed_blocks_known_stale_mirror() -> None:
    with pytest.raises(ValueError, match="blocked source repository"):
        assert_repository_allowed("rolandmccarthy13/free-proxy-list")


def test_assert_repository_allowed_is_case_and_whitespace_insensitive() -> None:
    """The block list must not be bypassable with a differently-cased or
    padded spelling of the same repository."""
    with pytest.raises(ValueError):
        assert_repository_allowed("  RolandMcCarthy13/Free-Proxy-List  ")
