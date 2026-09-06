# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from typing import Any

from configstream.history.tracker import ProxyHistoryTracker


class _RecordingConnection:
    def __init__(self, rows: list[tuple[str, float]] | None = None) -> None:
        self.rows = rows or []
        self.calls: list[tuple[str, list[str]]] = []

    def execute(self, query: str, params: list[str]) -> list[tuple[str, float]]:
        self.calls.append((query, list(params)))
        return self.rows


class _Storage:
    def __init__(self, connection: _RecordingConnection) -> None:
        self.connection = connection

    def get_connection(self) -> _RecordingConnection:
        return self.connection

    def close(self) -> None:
        return None


def _tracker(connection: _RecordingConnection) -> ProxyHistoryTracker:
    return ProxyHistoryTracker(_Storage(connection))


def test_bulk_stats_scopes_query_to_requested_ids() -> None:
    connection = _RecordingConnection([("wanted", 0.75)])
    tracker = _tracker(connection)

    result = tracker.get_bulk_stats(["wanted", "wanted"])

    assert result == {"wanted": {"reliability": 0.75, "uptime": 75.0}}
    assert len(connection.calls) == 1
    query, params = connection.calls[0]
    assert "WHERE proxy_id IN (?)" in query
    assert params == ["wanted"]


def test_bulk_stats_empty_request_avoids_database_query() -> None:
    connection = _RecordingConnection()
    tracker = _tracker(connection)

    assert tracker.get_bulk_stats([]) == {}
    assert connection.calls == []


def test_bulk_stats_chunks_large_requested_id_sets() -> None:
    connection = _RecordingConnection()
    tracker = _tracker(connection)
    proxy_ids = [f"proxy-{index}" for index in range(901)]

    assert tracker.get_bulk_stats(proxy_ids) == {}
    assert [len(params) for _query, params in connection.calls] == [900, 1]
    assert all("WHERE proxy_id IN (" in query for query, _params in connection.calls)
