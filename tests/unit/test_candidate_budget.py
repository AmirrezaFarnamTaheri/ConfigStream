# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from configstream.candidate_budget import select_source_candidates


def test_candidate_budget_deduplicates_and_bounds_deterministically() -> None:
    source = "https://example.com/subscription.txt"
    lines = [f"vless://candidate-{index}" for index in range(12)]
    lines.insert(4, lines[2])

    first, duplicate_drops, budget_drops = select_source_candidates(
        lines, source=source, limit=5
    )
    second, duplicate_drops_2, budget_drops_2 = select_source_candidates(
        lines, source=source, limit=5
    )

    assert first == second
    assert len(first) == 5
    assert len(set(first)) == 5
    assert duplicate_drops == duplicate_drops_2 == 1
    assert budget_drops == budget_drops_2 == 7


def test_candidate_budget_preserves_protocol_families_when_capacity_allows() -> None:
    lines = [
        "vless://a",
        "vless://b",
        "vmess://a",
        "trojan://a",
        "ss://a",
        '{"type":"wireguard","tag":"wg"}',
    ]

    selected, duplicate_drops, budget_drops = select_source_candidates(
        lines,
        source="https://example.com/mixed",
        limit=5,
    )

    assert duplicate_drops == 0
    assert budget_drops == 1
    assert any(value.startswith("vless://") for value in selected)
    assert any(value.startswith("vmess://") for value in selected)
    assert any(value.startswith("trojan://") for value in selected)
    assert any(value.startswith("ss://") for value in selected)
    assert any(value.startswith("{") for value in selected)


def test_candidate_budget_keeps_original_order_when_under_limit() -> None:
    lines = ["trojan://z", "ss://a", "vless://b"]

    selected, duplicate_drops, budget_drops = select_source_candidates(
        lines, source="https://example.com/small", limit=10
    )

    assert selected == lines
    assert duplicate_drops == 0
    assert budget_drops == 0


def test_candidate_budget_uses_source_scoped_selection() -> None:
    lines = [f"vless://candidate-{index}" for index in range(100)]

    first, _, _ = select_source_candidates(
        lines, source="https://a.example/sub", limit=10
    )
    second, _, _ = select_source_candidates(
        lines, source="https://b.example/sub", limit=10
    )

    assert first != second


@pytest.mark.parametrize("limit", [0, -1, True])
def test_candidate_budget_rejects_non_positive_or_boolean_limits(limit: int) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        select_source_candidates(
            ["vless://a"], source="https://example.com", limit=limit
        )
