"""Tests for AdaptiveTimeout."""

import pytest
import statistics
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.configstream.adaptive_timeout import AdaptiveTimeout


def test_initialization():
    # It attempts to load history immediately. If file doesn't exist, it uses initial.
    # But if tests run in parallel or share env, there might be a file?
    # Or maybe it defaults to 10.0 if not overridden properly?

    # In __init__: self.current_timeout = initial. Then _load_history().
    # If history file defaults to data/timeout_history.json and it exists from previous runs, it loads it.

    # We should ensure no file exists or pass a non-existent path.
    at = AdaptiveTimeout(initial=5.0, history_file=Path("nonexistent.json"))
    assert at.current_timeout == 5.0
    assert at.get_timeout("any") == 5.0


def test_load_history(tmp_path):
    hist = tmp_path / "hist.json"
    hist.write_text(json.dumps({"last_timeout": 8.0}))

    at = AdaptiveTimeout(history_file=hist)
    assert at.current_timeout == 8.0


def test_load_history_fail(tmp_path):
    hist = tmp_path / "hist.json"
    hist.write_text("invalid")

    at = AdaptiveTimeout(history_file=hist, initial=5.0)
    assert at.current_timeout == 5.0  # Unchanged


def test_record_update():
    # Use custom history file to avoid loading existing one
    at = AdaptiveTimeout(
        initial=10.0, min_t=1.0, max_t=20.0, history_file=Path("dummy")
    )

    # Add low latencies
    for _ in range(20):
        at.record("src", 0.5)

    # p95 of 0.5 is 0.5. Target = 1.0.
    # Moving from 10.0 towards 1.0
    assert at.current_timeout < 10.0

    # Add high latencies
    for _ in range(20):
        at.record("src", 5.0)

    # p95 around 5.0. Target = 10.0.
    # Should move up
    assert at.current_timeout > 2.0


def test_jitter():
    at = AdaptiveTimeout(history_file=Path("dummy"))
    assert at.get_jitter("src") == 0.0

    at.record("src", 1.0)
    assert at.get_jitter("src") == 0.0  # < 2 samples

    at.record("src", 2.0)
    # stdev([1.0, 2.0]) -> ~0.707
    jitter = at.get_jitter("src")
    assert 0.7 < jitter < 0.71


def test_save(tmp_path):
    hist = tmp_path / "hist.json"
    at = AdaptiveTimeout(history_file=hist, initial=7.5)
    at.save()

    assert hist.exists()
    data = json.loads(hist.read_text())
    assert data["last_timeout"] == 7.5


def test_save_fail(tmp_path):
    # Directory permission error simulation or similar
    # We mock write_text
    hist = tmp_path / "hist.json"
    at = AdaptiveTimeout(history_file=hist)

    with patch.object(Path, "write_text", side_effect=Exception("Fail")):
        at.save()  # Should log warning but not crash


def test_update_statistics_error():
    at = AdaptiveTimeout(history_file=Path("dummy"))
    # Mock statistics.quantiles to raise error even if list has items
    with patch("statistics.quantiles", side_effect=statistics.StatisticsError("Err")):
        at.latencies = [1.0, 2.0]
        at.update()  # Should catch and log


def test_record_high_latency(caplog):
    at = AdaptiveTimeout(history_file=Path("dummy"))
    with patch("src.configstream.adaptive_timeout.logger") as mock_logger:
        at.record("src", 101.0)
        assert mock_logger.debug.called
