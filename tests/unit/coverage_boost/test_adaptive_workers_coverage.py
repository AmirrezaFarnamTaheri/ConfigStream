# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.adaptive_workers import calculate_optimal_workers, _is_ci_environment
from unittest.mock import patch, MagicMock


def test_calculate_optimal_workers_requested():
    assert calculate_optimal_workers(10) == 10


def test_calculate_optimal_workers_auto():
    with patch("multiprocessing.cpu_count", return_value=4):
        # Mock psutil not present (fallback to CPU logic)
        with patch("configstream.adaptive_workers.psutil_module", None):
            # [FIX] Updated: non-CI = 4 * 15 = 60, CI = 4 * 10 = 40
            # Mock CI detection to False for deterministic test
            with patch("configstream.adaptive_workers._is_ci_environment", return_value=False):
                assert calculate_optimal_workers(0) == 60


def test_calculate_optimal_workers_ci_mode():
    """Test that CI environments get lower worker limits."""
    with patch("multiprocessing.cpu_count", return_value=4):
        with patch("configstream.adaptive_workers.psutil_module", None):
            with patch("configstream.adaptive_workers._is_ci_environment", return_value=True):
                # CI: 4 * 10 = 40, capped at 50
                assert calculate_optimal_workers(0) == 40


def test_calculate_optimal_workers_with_memory_constraint():
    with patch("multiprocessing.cpu_count", return_value=32):
        mock_psutil = MagicMock()
        mock_mem = MagicMock()
        # 1GB available = 1024 MB. (1024 - 500) / 20 = 26 workers
        mock_mem.available = 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_mem

        with patch("configstream.adaptive_workers.psutil_module", mock_psutil):
            with patch("configstream.adaptive_workers._is_ci_environment", return_value=False):
                workers = calculate_optimal_workers(0)
                assert workers == 26


def test_calculate_optimal_workers_hard_limits():
    with patch("multiprocessing.cpu_count", return_value=128):
        mock_psutil = MagicMock()
        mock_mem = MagicMock()
        mock_mem.available = 64 * 1024 * 1024 * 1024  # Huge RAM
        mock_psutil.virtual_memory.return_value = mock_mem

        with patch("configstream.adaptive_workers.psutil_module", mock_psutil):
            with patch("configstream.adaptive_workers._is_ci_environment", return_value=False):
                workers = calculate_optimal_workers(0)
                # [FIX] Updated: max is now 150 (non-CI) instead of 200
                assert workers <= 150

            with patch("configstream.adaptive_workers._is_ci_environment", return_value=True):
                workers = calculate_optimal_workers(0)
                # CI max is 50
                assert workers <= 50


def test_calculate_optimal_workers_exception():
    with patch("multiprocessing.cpu_count", side_effect=Exception("Error")):
        assert calculate_optimal_workers(0) == 20  # Fallback


def test_is_ci_environment():
    """Test CI detection function."""
    with patch.dict("os.environ", {"CI": "true"}, clear=False):
        assert _is_ci_environment() is True
    with patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}, clear=False):
        assert _is_ci_environment() is True
    with patch.dict("os.environ", {}, clear=True):
        assert _is_ci_environment() is False
