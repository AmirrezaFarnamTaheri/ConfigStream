"""Adaptive worker scaling based on system resources."""

import os

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


def calculate_optimal_workers(max_workers: int = 32, min_workers: int = 8) -> int:
    """
    Calculate optimal number of workers based on CPU and memory.

    Args:
        max_workers: Maximum number of workers
        min_workers: Minimum number of workers

    Returns:
        Optimal worker count
    """
    try:
        # Get CPU count
        cpu_count = os.cpu_count() or 4

        # If psutil is not available, return a reasonable default
        if psutil is None:
            return min(max_workers, cpu_count * 4)

        # Get CPU usage (lower usage = more workers available)
        cpu_usage = psutil.cpu_percent(interval=0.1)

        # Get memory usage
        memory = psutil.virtual_memory()
        memory_available_pct = 1 - memory.percent / 100

        # Calculate optimal workers
        # Base on CPU count, adjusted by current usage
        base_workers = cpu_count * 4  # 4x CPU count as baseline

        # Scale down if CPU is busy
        cpu_factor = max(0.5, 1.0 - (cpu_usage / 200))  # 50% at 100% CPU

        # Scale down if memory is low
        memory_factor = max(0.5, memory_available_pct)

        optimal = int(base_workers * cpu_factor * memory_factor)

        # Clamp to min/max
        return max(min_workers, min(optimal, max_workers))

    except Exception:
        # Fallback to safe default
        return 16
