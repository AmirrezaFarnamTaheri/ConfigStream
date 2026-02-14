# SPDX-License-Identifier: AGPL-3.0-or-later
from configstream.adaptive_workers import calculate_optimal_workers
from unittest.mock import patch


def test_adaptive_workers_calc():
    # Patch multiprocessing.cpu_count (used by the module) not os.cpu_count
    with patch("multiprocessing.cpu_count", return_value=4):
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value.available = 2 * 1024 * 1024 * 1024  # 2GB
            workers = calculate_optimal_workers()
            assert workers > 0
            # Logic: CPU * multiplier (15 for non-CI), constrained by memory
            # 4 * 15 = 60, Memory: (2048 - 500) / 20 = 77.4
            # Result: min(60, 77) = 60, capped at 150
            assert 20 <= workers <= 80
