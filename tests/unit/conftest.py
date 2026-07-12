# SPDX-License-Identifier: AGPL-3.0-or-later
"""Narrow fixtures for unit tests that inject an ordinary HTTPX client."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest


@pytest.fixture(autouse=True)
def _logical_url_fetcher_fixture(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep RESPX redirect tests on logical URLs.

    Production clients use ``SecurityTransport`` for DNS validation and IP pinning.
    These tests inject a plain HTTPX client to exercise redirect/retry behavior, so
    high-level DNS validation must not rewrite their URL before RESPX sees it.
    Dedicated transport and private-DNS tests remain untouched.
    """

    logical_url_tests = {
        "test_fetch_from_source_follows_safe_redirect",
        "test_fetch_from_source_rejects_private_redirect",
        "test_fetch_from_source_limits_redirect_depth",
    }
    if request.node.name in logical_url_tests:

        async def no_dns_rewrite(*args: object, **kwargs: object) -> tuple[None, None]:
            return None, None

        monkeypatch.setattr(
            "configstream.pipeline.fetcher._reject_source_dns",
            no_dns_rewrite,
        )
        return

    if request.node.name == "test_fetch_from_source_validates_redirect_dns_before_fetch":

        async def validate_redirect(
            url: str,
            *args: object,
            **kwargs: object,
        ) -> tuple[str | None, None]:
            if "safe-name.example" in url:
                return "Source URL host resolves to a private or non-global address", None
            return None, None

        monkeypatch.setattr(
            "configstream.pipeline.fetcher._reject_source_dns",
            validate_redirect,
        )
