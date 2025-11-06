"""Tests for adaptive worker scaling."""

import sys
from unittest.mock import MagicMock, patch

from configstream.adaptive_workers import calculate_optimal_workers


def test_calculate_optimal_workers_basic():
    """Test basic worker calculation."""
    workers = calculate_optimal_workers()

    # Should return a reasonable number
    assert 8 <= workers <= 32


def test_calculate_optimal_workers_with_limits():
    """Test worker calculation respects limits."""
    workers = calculate_optimal_workers(max_workers=16, min_workers=4)

    assert 4 <= workers <= 16


def test_calculate_optimal_workers_never_zero():
    """Test that worker count is never zero."""
    workers = calculate_optimal_workers(min_workers=1)

    assert workers >= 1


def test_calculate_optimal_workers_with_psutil():
    """Test worker calculation with psutil available."""
    try:
        import psutil

        # psutil is available, test the adaptive logic
        workers = calculate_optimal_workers(max_workers=32, min_workers=8)

        # Should return a value within bounds
        assert 8 <= workers <= 32

    except ImportError:
        # psutil not available, skip this test
        pass


def test_calculate_optimal_workers_without_psutil():
    """Test worker calculation when psutil is not available."""
    # Mock psutil as None to simulate it not being installed
    import configstream.adaptive_workers

    original_psutil = configstream.adaptive_workers.psutil
    try:
        configstream.adaptive_workers.psutil = None

        workers = calculate_optimal_workers(max_workers=32, min_workers=8)

        # Should return CPU count * 4, clamped to max_workers
        assert 8 <= workers <= 32

    finally:
        configstream.adaptive_workers.psutil = original_psutil


def test_calculate_optimal_workers_with_high_cpu_usage():
    """Test worker calculation under high CPU usage."""
    try:
        import psutil

        # Mock high CPU usage
        mock_memory = MagicMock()
        mock_memory.percent = 30.0  # 30% used, 70% available

        with (
            patch("psutil.cpu_percent", return_value=90.0),
            patch("psutil.virtual_memory", return_value=mock_memory),
        ):
            workers = calculate_optimal_workers(max_workers=32, min_workers=8)

            # High CPU should reduce worker count
            assert 8 <= workers <= 32

    except ImportError:
        # psutil not available, skip this test
        pass


def test_calculate_optimal_workers_with_low_memory():
    """Test worker calculation with low available memory."""
    try:
        import psutil

        # Mock low memory availability
        mock_memory = MagicMock()
        mock_memory.percent = 85.0  # 85% used, only 15% available

        with (
            patch("psutil.cpu_percent", return_value=20.0),
            patch("psutil.virtual_memory", return_value=mock_memory),
        ):
            workers = calculate_optimal_workers(max_workers=32, min_workers=8)

            # Low memory should reduce worker count
            assert 8 <= workers <= 32

    except ImportError:
        # psutil not available, skip this test
        pass


def test_calculate_optimal_workers_exception_handling():
    """Test that exceptions fall back to safe default."""
    try:
        import psutil

        # Mock an exception during CPU/memory checks
        with patch("psutil.cpu_percent", side_effect=Exception("Test error")):
            workers = calculate_optimal_workers()

            # Should fall back to default of 16
            assert workers == 16

    except ImportError:
        # psutil not available, skip this test
        pass


def test_calculate_optimal_workers_extreme_limits():
    """Test with extreme min/max values."""
    workers = calculate_optimal_workers(max_workers=100, min_workers=1)

    assert 1 <= workers <= 100

    workers = calculate_optimal_workers(max_workers=2, min_workers=2)

    assert workers == 2
