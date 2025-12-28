"""
Scoring logic for source quality.
"""

import math
from typing import Dict, List

from ..models import Proxy


def calculate_diversity_score(proxies: List[Proxy]) -> float:
    """
    Calculates a Gini-Simpson based diversity score for a list of proxies based on country.
    Score ranges from 0.0 (all same country) to 1.0 (perfectly distributed).
    """
    if not proxies:
        return 0.0

    counts: Dict[str, int] = {}
    total = len(proxies)
    for p in proxies:
        cc = p.country_code or "XX"
        counts[cc] = counts.get(cc, 0) + 1

    # Gini-Simpson Index: 1 - sum(p^2)
    sum_sq_probs = sum((c / total) ** 2 for c in counts.values())
    diversity_index = 1.0 - sum_sq_probs

    return diversity_index


def calculate_cooldown_hours(consecutive_failures: int) -> float:
    """
    Calculate cooldown hours based on consecutive failures using exponential backoff.
    """
    if consecutive_failures <= 0:
        return 0.0

    # 1 failure -> 1h, 2 -> 4h, 3 -> 8h... capped at 48h
    return min(48.0, math.pow(2, consecutive_failures))


def calculate_trust_score(
    reliability_score: float,
    diversity_score: float,
    consecutive_failures: int,
    avg_jitter: float,
) -> float:
    """
    Calculate trust score based on multiple factors.

    Args:
        reliability_score: 0-100 score based on yield rate
        diversity_score: 0.0-1.0 score
        consecutive_failures: Number of recent failures
        avg_jitter: Average jitter in seconds
    """
    consistency_score = max(0, 100 - (consecutive_failures * 10))

    # Jitter Penalty: If jitter > 1.0s, penalize score
    jitter_penalty = min(20, avg_jitter * 10) if avg_jitter > 1.0 else 0

    trust_score = (
        (reliability_score * 0.5)
        + (diversity_score * 100 * 0.3)
        + (consistency_score * 0.2)
    ) - jitter_penalty

    return max(0.0, trust_score)
