# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for history components."""

import json
from pathlib import Path
from unittest.mock import patch

from configstream.history.storage import HistoryStorage
from configstream.history.analytics import HistoryAnalytics
from configstream.history.export import HistoryExporter

# --- Storage Tests ---


def test_storage_load_save(tmp_path):
    history_file = tmp_path / "history.json"
    storage = HistoryStorage(history_file)

    # Load empty
    assert storage.load_history() == {}

    # Save
    data = {"test": "data"}
    storage.save_history(data)

    # Load
    loaded = storage.load_history()
    assert loaded == data


def test_storage_file_too_large(tmp_path):
    history_file = tmp_path / "history.json"
    history_file.write_text("a")
    storage = HistoryStorage(history_file)

    with patch.object(Path, "stat") as mock_stat:
        mock_stat.return_value.st_size = 101 * 1024 * 1024  # 101MB
        assert storage.load_history() == {}


def test_storage_load_error(tmp_path):
    history_file = tmp_path / "history.json"
    history_file.write_text("invalid json")
    storage = HistoryStorage(history_file)
    assert storage.load_history() == {}


def test_storage_save_error(tmp_path):
    # Directory not writable or other error
    history_file = tmp_path / "nonexistent" / "history.json"
    # We rely on mkdir in init, but if we mess it up after
    storage = HistoryStorage(history_file)

    with patch(
        "configstream.utils.AtomicFileWriter.write_text",
        side_effect=Exception("Fail"),
    ):
        storage.save_history({})  # Should catch exception and log error


# --- Analytics Tests ---


def test_analytics_reliability():
    # Empty/None
    assert HistoryAnalytics.get_reliability_score(None) == 0.5
    assert HistoryAnalytics.get_reliability_score({}) == 0.5

    # With data
    history = {
        "entries": [
            {"is_working": True},
            {"is_working": False},
            {"is_working": True},
            {"is_working": True},
        ]
    }
    assert HistoryAnalytics.get_reliability_score(history) == 0.75


def test_analytics_trend():
    history = {
        "entries": [
            {"timestamp": "2023-01-01", "latency": 100, "is_working": True},
            {"timestamp": "2023-01-02", "latency": None, "is_working": False},
        ]
    }
    trend = HistoryAnalytics.get_trend_data(history)
    assert trend["timestamps"] == ["2023-01-01", "2023-01-02"]
    assert trend["latencies"] == [100, 0]
    assert trend["status"] == [1, 0]


def test_analytics_history_points():
    history = {
        "entries": [
            {"timestamp": "2023-01-01", "latency": 100, "is_working": True},
            {"timestamp": "2023-01-02", "latency": None, "is_working": False},
            {"timestamp": "2023-01-03", "latency": 200, "is_working": True},
        ]
    }
    points = HistoryAnalytics.get_history_points(history)
    assert points == [100.0, 9999.0, 200.0]


def test_analytics_summary():
    assert HistoryAnalytics.get_summary_stats({})["total_tests"] == 0

    history = {
        "entries": [
            {"latency": 100, "is_working": True},
            {"latency": 200, "is_working": True},
            {"latency": None, "is_working": False},
        ]
    }
    stats = HistoryAnalytics.get_summary_stats(history)
    assert stats["total_tests"] == 3
    assert stats["success_rate"] == 2 / 3
    assert stats["avg_latency"] == 150.0
    assert stats["min_latency"] == 100
    assert stats["max_latency"] == 200


# --- Export Tests ---


def test_export_visualization(tmp_path):
    output = tmp_path / "viz.json"
    history_data = {
        "config1": {
            "protocol": "ss",
            "address": "1.1.1.1",
            "port": 443,
            "entries": [
                {"timestamp": "2023-01-01", "latency": 100, "is_working": True}
            ],
        },
        "config2": {"entries": []},  # Should be skipped
    }

    HistoryExporter.export_for_visualization(history_data, output)
    assert output.exists()
    data = json.loads(output.read_text())
    assert "config1" in data
    assert "config2" not in data
    assert data["config1"]["protocol"] == "ss"


def test_export_active_trend(tmp_path):
    output = tmp_path / "trend.json"

    with patch("configstream.history.export.datetime") as mock_dt:
        mock_dt.now.return_value.replace.return_value = mock_dt.now.return_value
        # Set fixed "now"
        fixed_now = datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = fixed_now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.min = datetime.min

        history_data = {
            "c1": {
                "entries": [
                    # Working, recent (1 hour ago)
                    {"timestamp": "2023-10-27T11:00:00+00:00", "is_working": True},
                    # Working, old (8 days ago)
                    {"timestamp": "2023-10-19T11:00:00+00:00", "is_working": True},
                ]
            }
        }

        HistoryExporter.export_active_proxy_trend(
            history_data, output, hours_to_track=24
        )

        assert output.exists()
        data = json.loads(output.read_text())
        assert len(data) == 1
        assert data[0]["active_count"] == 1


def test_export_active_trend_empty(tmp_path):
    output = tmp_path / "trend_empty.json"
    HistoryExporter.export_active_proxy_trend({}, output)
    assert output.exists()
    assert json.loads(output.read_text()) == []


# noqa: E402
# noqa: E402
from datetime import datetime, timezone
