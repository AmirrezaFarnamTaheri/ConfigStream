"""
Adaptive Worker Scaling.
Calculates safe thread/worker counts based on container resource limits.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None

def calculate_optimal_workers(max_workers: int = 50, min_workers: int = 4) -> int:
    """
    Determine optimal concurrency based on available CPU/RAM.
    """
    try:
        # 1. CPU Check
        cpu_count = os.cpu_count() or 2

        # 2. Memory Check (if psutil available)
        mem_factor = 1.0
        if psutil:
            try:
                vm = psutil.virtual_memory()
                if vm.percent > 85:
                    mem_factor = 0.5
                elif vm.percent > 70:
                    mem_factor = 0.75
            except Exception:
                pass

        # Baseline: 5 workers per CPU core is usually safe for IO-bound work
        # But we cap it based on memory pressure
        optimal = int((cpu_count * 5) * mem_factor)

        # Clamp results
        result = max(min_workers, min(optimal, max_workers))

        logger.info(
            "Adaptive Scaling: CPUs=%d, MemFactor=%.2f -> Workers=%d",
            cpu_count, mem_factor, result
        )
        return result

    except Exception as e:
        logger.warning("Error calculating workers: %s. Using default.", e)
        return 10
