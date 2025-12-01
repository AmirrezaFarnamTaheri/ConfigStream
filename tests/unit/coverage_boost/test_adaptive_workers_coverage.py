import pytest
from configstream.adaptive_workers import calculate_optimal_workers
from unittest.mock import patch, MagicMock


def test_calculate_optimal_workers_requested():
    assert calculate_optimal_workers(10) == 10


def test_calculate_optimal_workers_auto():
    with patch("multiprocessing.cpu_count", return_value=4):
        # Mock psutil not present (fallback to CPU logic)
        with patch("configstream.adaptive_workers.psutil_module", None):
            # 4 cores * 15 = 60
            assert calculate_optimal_workers(0) == 60


def test_calculate_optimal_workers_with_memory_constraint():
    with patch("multiprocessing.cpu_count", return_value=32):
        # 32 * 15 = 480 (usually high)

        # Mock psutil
        mock_psutil = MagicMock()
        mock_mem = MagicMock()
        # 1GB available = 1024 MB.
        # (1024 - 500) / 20 = 524 / 20 = 26 workers
        mock_mem.available = 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_mem

        with patch("configstream.adaptive_workers.psutil_module", mock_psutil):
            workers = calculate_optimal_workers(0)
            assert workers == 26


def test_calculate_optimal_workers_hard_limits():
    with patch("multiprocessing.cpu_count", return_value=128):  # Huge CPU

        mock_psutil = MagicMock()
        mock_mem = MagicMock()
        mock_mem.available = 64 * 1024 * 1024 * 1024  # Huge RAM
        mock_psutil.virtual_memory.return_value = mock_mem

        with patch("configstream.adaptive_workers.psutil_module", mock_psutil):
            workers = calculate_optimal_workers(0)
            assert workers <= 200  # Max limit


def test_calculate_optimal_workers_exception():
    with patch("multiprocessing.cpu_count", side_effect=Exception("Error")):
        assert calculate_optimal_workers(0) == 20  # Fallback
