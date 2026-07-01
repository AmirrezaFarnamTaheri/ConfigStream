# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Adaptive Worker Calculation.
Determines optimal worker count based on CPU cores and memory.
"""

import logging
import multiprocessing
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import psutil, handle failure gracefully
# We define a module-level variable to hold the module or None
psutil_module: Optional[Any]
try:
    import psutil as psutil_module  # type: ignore
except ImportError:
    psutil_module = None


def _is_ci_environment() -> bool:
    """Detect CI/CD environments to apply conservative limits."""
    ci_vars = ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "CIRCLECI")
    return any(os.environ.get(v) for v in ci_vars)


def calculate_optimal_workers(requested: int = 0) -> int:
    """
    Calculate safe worker count.
    0 = Auto-detect.

    Added CI detection with conservative upper bound (50) to prevent
    OOM on GitHub Actions runners (2 cores, ~7GB RAM). Also lowered the
    general upper bound from 200 to 150 as 200 was too aggressive for most
    environments.
    """
    if requested > 0:
        return requested

    try:
        cpu_count = multiprocessing.cpu_count()
        is_ci = _is_ci_environment()

        # Basic heuristic: 10-15 workers per core for IO-bound tasks
        # ConfigStream is IO-bound (network) but CPU-bound (parsing)
        multiplier = 10 if is_ci else 15
        optimal = cpu_count * multiplier

        # Memory check (if psutil available)
        if psutil_module:
            mem = psutil_module.virtual_memory()
            # Reserve 500MB system overhead, assume 20MB per worker
            available_mb = (mem.available / 1024 / 1024) - 500
            if available_mb <= 0:
                # Not enough memory for even the safety buffer, use a safe minimum.
                max_by_mem = 10
            else:
                max_by_mem = int(max(10, available_mb / 20))

            optimal = min(optimal, max_by_mem)

        # Lower upper bound; CI gets much tighter cap
        hard_max = 50 if is_ci else 150
        optimal = max(10, min(hard_max, optimal))

        env_label = " (CI)" if is_ci else ""
        logger.info(f"Auto-calculated optimal workers: {optimal}{env_label}")
        return optimal

    except Exception as e:
        logger.warning(f"Failed to calculate optimal workers: {e}")
        return 20  # Safe fallback
