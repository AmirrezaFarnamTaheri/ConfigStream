# SPDX-License-Identifier: AGPL-3.0-or-later
"""Chain metadata must never imply an unobserved end-to-end success."""

from __future__ import annotations

from configstream.output_handler import (
    _chain_obs_to_entries,
    _chain_to_proxy_entry,
    _group_chain_obs,
    _is_clean_ip,
    _save_clean_ips,
)
import json


def _outbound(tag: str, detour: str = "") -> dict:
    row = {"tag": tag, "type": "socks", "server": "1.1.1.1", "server_port": 1080}
    if detour:
        row["detour"] = detour
    return row


def test_generated_washed_and_smart_chains_are_unverified_candidates() -> None:
    for process in ("washed", "chain", "shielded"):
        row = _chain_to_proxy_entry([_outbound("relay")], process=process)
        assert row["is_working"] is False
        assert row["last_checked"] == ""
        assert "candidate" in row["tags"]
        assert row["details"]["chain_verified"] is False


def test_washed_chain_entries_cannot_inflate_public_working_count() -> None:
    rows = _chain_obs_to_entries(
        [_outbound("relay")], {"smart": [[_outbound("other")]]}
    )
    assert len(rows) == 2
    assert all(not row["is_working"] for row in rows)


def test_invalid_detour_graphs_fail_closed() -> None:
    assert (
        _group_chain_obs(
            [_outbound("a", "b"), _outbound("b", "a"), _outbound("entry", "a")]
        )
        == []
    )
    assert _group_chain_obs([_outbound("entry", "missing")]) == []
    assert (
        _group_chain_obs(
            [_outbound("dupe"), _outbound("dupe"), _outbound("entry", "dupe")]
        )
        == []
    )


def test_independent_valid_chain_survives_an_invalid_cycle() -> None:
    chains = _group_chain_obs(
        [
            _outbound("a", "b"),
            _outbound("b", "a"),
            _outbound("legit", "exit"),
            _outbound("exit"),
        ]
    )
    assert len(chains) == 1
    assert [row["tag"] for row in chains[0]] == ["exit", "legit"]


def test_clean_ip_writer_requires_valid_global_ip_and_port(tmp_path) -> None:
    assert not _is_clean_ip("2001:db8:::1")
    assert not _is_clean_ip("1::2::3")
    assert not _is_clean_ip("127.0.0.1")
    assert _is_clean_ip("2606:4700:4700::1111")
    path = tmp_path / "data" / "clean_ips.json"
    _save_clean_ips(
        [
            ("1.1.1.1", 443),
            ("1.1.1.1", 0),
            ("1.1.1.1", 65536),
            ("2606:4700:4700::1111", 2408),
            ("2606:4700:4700::1111", "bad"),  # type: ignore[list-item]
            ("1::2::3", 443),
        ],
        path,
    )
    assert json.loads(path.read_text()) == [
        {"ip": "1.1.1.1", "port": 443},
        {"ip": "2606:4700:4700::1111", "port": 2408},
    ]
