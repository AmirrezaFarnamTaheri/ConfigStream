
import pytest
from configstream.adaptive_workers import calculate_optimal_workers
from unittest.mock import patch

def test_adaptive_workers_calc():
    # CPU bound
    with patch('os.cpu_count', return_value=4):
        with patch('psutil.virtual_memory') as mock_mem:
            mock_mem.return_value.available = 2 * 1024 * 1024 * 1024 # 2GB
            workers = calculate_optimal_workers()
            assert workers > 0
            # Logic: min(CPU*50, RAM/50MB)
            # 4*50 = 200
            # 2000/50 = 40
            # Should be around 40
            assert 20 <= workers <= 60
