# SPDX-License-Identifier: AGPL-3.0-or-later
"""Canonical external-source registry.

Repository names and URLs are not trusted identities.  Providers are resolved
through this registry so ownership, licensing, update cadence, and resource
budgets remain explicit and reviewable.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .models import SourceProvider, TrustClass

DATABAY = SourceProvider(
    provider_id="databay-free-proxy-list",
    display_name="Databay Free Proxy List",
    canonical_owner="databay-labs",
    canonical_repository="free-proxy-list",
    allowed_mirrors=frozenset(),
    trust_class=TrustClass.OPAQUE,
    license_spdx="MIT",
    declared_protocols=frozenset({"http", "socks4", "socks5"}),
    max_snapshot_age_seconds=30 * 60,
    max_response_bytes=32 * 1024 * 1024,
    max_records=250_000,
    expected_update_interval_seconds=5 * 60,
    minimum_records=1,
    maximum_record_delta_ratio=0.90,
    source_policy_version="1",
)

PROXIFLY = SourceProvider(
    provider_id="proxifly-free-proxy-list",
    display_name="Proxifly Free Proxy List",
    canonical_owner="proxifly",
    canonical_repository="free-proxy-list",
    allowed_mirrors=frozenset(),
    trust_class=TrustClass.COMMUNITY,
    license_spdx=None,
    declared_protocols=frozenset({"http", "https", "socks4", "socks5"}),
    max_snapshot_age_seconds=30 * 60,
    max_response_bytes=32 * 1024 * 1024,
    max_records=500_000,
    expected_update_interval_seconds=5 * 60,
    minimum_records=1,
    maximum_record_delta_ratio=0.95,
    source_policy_version="1",
)

PROVIDERS: Mapping[str, SourceProvider] = MappingProxyType(
    {provider.provider_id: provider for provider in (DATABAY, PROXIFLY)}
)

# These identities are intentionally not aliases.  They are stale, ownership-
# ambiguous, or otherwise prohibited from production acquisition.
BLOCKED_REPOSITORIES: Mapping[str, str] = MappingProxyType(
    {
        "rolandmccarthy13/free-proxy-list": (
            "stale historical mirror; README resolves to a different canonical owner"
        )
    }
)


def get_provider(provider_id: str) -> SourceProvider:
    try:
        return PROVIDERS[provider_id]
    except KeyError as exc:
        raise KeyError(f"unknown source provider: {provider_id}") from exc


def assert_repository_allowed(repository_full_name: str) -> None:
    normalized = repository_full_name.strip().lower()
    reason = BLOCKED_REPOSITORIES.get(normalized)
    if reason:
        raise ValueError(f"blocked source repository {normalized}: {reason}")
