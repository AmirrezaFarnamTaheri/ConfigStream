"""
Adaptive Worker Calculation.
Determines optimal worker count based on CPU cores and memory.
"""

import logging
import multiprocessing
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import psutil, handle failure gracefully
# We define a module-level variable to hold the module or None
psutil_module: Optional[Any]
try:
    import psutil as psutil_module  # type: ignore
except ImportError:
    psutil_module = None


def calculate_optimal_workers(requested: int = 0) -> int:
    """
    Calculate safe worker count.
    0 = Auto-detect.
    """
    if requested > 0:
        return requested

    try:
        cpu_count = multiprocessing.cpu_count()

        # Basic heuristic: 10-20 workers per core for IO-bound tasks
        # ConfigStream is IO-bound (network) but CPU-bound (parsing)
        optimal = cpu_count * 15

        # Memory check (if psutil available)
        if psutil_module:
            mem = psutil_module.virtual_memory()
            # Reserve 500MB system overhead, assume 20MB per worker
            available_mb = (mem.available / 1024 / 1024) - 500
            max_by_mem = int(max(10, available_mb / 20))

            optimal = min(optimal, max_by_mem)

        # Hard limits
        optimal = max(10, min(200, optimal))

        logger.info(f"Auto-calculated optimal workers: {optimal}")
        return optimal

    except Exception as e:
        logger.warning(f"Failed to calculate optimal workers: {e}")
        return 20  # Safe fallback
