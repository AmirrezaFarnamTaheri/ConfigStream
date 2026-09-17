# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deterministic resource bounds for untrusted remote source candidates."""

from __future__ import annotations

import hashlib
import heapq
from collections import defaultdict
from collections.abc import Sequence


def _candidate_family(value: str) -> str:
    """Return a coarse protocol family used to preserve rare candidate types."""

    text = value.lstrip()
    if not text:
        return "empty"
    if text.startswith("{"):
        return "json"
    marker = text.find("://")
    if 0 < marker <= 32:
        return text[:marker].lower()
    return "other"


def _rank_key(source: str, value: str) -> tuple[bytes, str]:
    """Return a stable source-scoped rank without exposing candidate contents."""

    digest = hashlib.sha256()
    digest.update(source.encode("utf-8", errors="surrogatepass"))
    digest.update(b"\0")
    digest.update(value.encode("utf-8", errors="surrogatepass"))
    return digest.digest(), value


def select_source_candidates(
    lines: Sequence[str], *, source: str, limit: int
) -> tuple[list[str], int, int]:
    """Bound one remote source before expensive network testing.

    Exact duplicate strings are removed first.  If the remaining source is over
    budget, selection is deterministic and source-scoped instead of taking the
    first N records.  At least one candidate from every observed protocol family
    is retained whenever the configured limit can represent all families.

    Returns ``(selected, exact_duplicates_dropped, budget_dropped)``.
    """

    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")

    unique = list(dict.fromkeys(lines))
    exact_duplicates_dropped = len(lines) - len(unique)
    if len(unique) <= limit:
        return unique, exact_duplicates_dropped, 0

    by_family: dict[str, list[str]] = defaultdict(list)
    for value in unique:
        by_family[_candidate_family(value)].append(value)

    family_winners = [
        min(values, key=lambda value: _rank_key(source, value))
        for _family, values in sorted(by_family.items())
    ]
    if len(family_winners) > limit:
        family_winners = heapq.nsmallest(
            limit,
            family_winners,
            key=lambda value: _rank_key(source, value),
        )

    selected_values = set(family_winners)
    remaining_slots = limit - len(selected_values)
    if remaining_slots > 0:
        remaining = (value for value in unique if value not in selected_values)
        selected_values.update(
            heapq.nsmallest(
                remaining_slots,
                remaining,
                key=lambda value: _rank_key(source, value),
            )
        )

    # Preserve upstream order among the selected records so downstream chunking
    # and logs remain stable while the selection itself is unbiased by position.
    selected = [value for value in unique if value in selected_values]
    budget_dropped = len(unique) - len(selected)
    return selected, exact_duplicates_dropped, budget_dropped
