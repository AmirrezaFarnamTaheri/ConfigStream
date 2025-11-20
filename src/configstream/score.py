"""Scoring helpers for ranking proxies across multiple dimensions."""

from __future__ import annotations

import math
from typing import Mapping, Optional, TYPE_CHECKING

from .config import AppSettings
from .models import Proxy

if TYPE_CHECKING:
    from .test_cache import TestResultCache


def _latency_points(lat_ms: float | None, soft_cap: int, max_points: float) -> float:
    """Calculate score points based on latency using sigmoid function."""
    if lat_ms is None or soft_cap <= 0:
        return 0.0
    center = max(1.0, soft_cap * 0.6)
    slope = max(50.0, soft_cap * 0.2)
    return max_points * (1.0 / (1.0 + math.exp((lat_ms - center) / slope)))


def calculate_health_score(
    proxy: Proxy,
    cache: Optional["TestResultCache"] = None,
    settings: Optional[AppSettings] = None,
) -> float:
    """
    Calculate comprehensive health score for a proxy.

    Scoring factors:
    - Historical success rate (40 points): How often the proxy works
    - Latency (30 points): Lower latency = higher score
    - Security features (20 points): TLS, AEAD encryption
    - Current working status (10 points): Currently working or not

    Args:
        proxy: Proxy to score
        cache: Optional test result cache for historical data
        settings: Optional app settings

    Returns:
        Health score between 0.0 and 100.0
    """
    if settings is None:
        settings = AppSettings()

    score = 0.0
    weights = settings.SCORE_WEIGHTS

    # Historical success rate
    w_hist = weights.get("historical_success", 40.0)
    if cache:
        historical_score = cache.get_health_score(proxy)
        score += historical_score * w_hist
    else:
        # Default neutral score (50%) if no history
        score += 0.5 * w_hist

    # Latency score
    w_lat = weights.get("latency", 30.0)
    if proxy.latency is not None:
        score += _latency_points(proxy.latency, settings.LAT_SOFT_CAP_MS, w_lat)
    else:
        # No latency data - assume average (50%)
        score += 0.5 * w_lat

    # Security features
    w_sec = weights.get("security", 20.0)
    security_score = 0.0
    if proxy.details:
        # Each feature contributes a fraction of the total security points
        if proxy.details.get("tls"):
            security_score += 0.5 * w_sec  # 50% of weight
        if proxy.details.get("aead"):
            security_score += 0.25 * w_sec  # 25% of weight
        if proxy.details.get("encryption"):
            security_score += 0.15 * w_sec  # 15% of weight
    if proxy.dns_over_https_ok:
        security_score += 0.1 * w_sec  # 10% of weight
    score += min(security_score, w_sec)

    # Current working status
    w_stat = weights.get("current_status", 10.0)
    if proxy.is_working:
        score += w_stat

    # Ensure score is between 0 and 100
    return round(min(max(score, 0.0), 100.0), 2)


def score_speed(
    proxy: Proxy, history: Mapping[str, Mapping[str, float]], settings: AppSettings
) -> float:
    """Legacy scoring function prioritizing speed."""
    score = _latency_points(proxy.latency_ms, settings.LAT_SOFT_CAP_MS, 70.0)
    if proxy.throughput_kbps:
        score += min(proxy.throughput_kbps, 5000) / 5000 * 20.0
    hist = history.get(proxy.id) or {}
    score += hist.get("success_rate", 0.0) * 10.0
    return round(score, 2)


def score_balanced(
    proxy: Proxy, history: Mapping[str, Mapping[str, float]], settings: AppSettings
) -> float:
    """Legacy scoring function for balanced performance."""
    score = _latency_points(proxy.latency_ms, settings.LAT_SOFT_CAP_MS, 50.0)
    hist = history.get(proxy.id) or {}
    score += hist.get("success_rate", 0.0) * 25.0
    score += max(0.0, 1.0 - (proxy.age_seconds or 0) / 86400.0) * 10.0
    details = proxy.details or {}
    privacy = 0.0
    if details.get("tls"):
        privacy += 2.0
    if details.get("aead"):
        privacy += 2.0
    if proxy.dns_over_https_ok:
        privacy += 1.0
    score += privacy
    return round(score, 2)


def score_privacy(
    proxy: Proxy, history: Mapping[str, Mapping[str, float]], settings: AppSettings
) -> float:
    """Legacy scoring function prioritizing privacy features."""
    details = proxy.details or {}
    base = 0.0
    if details.get("tls"):
        base += 35.0
    if details.get("aead"):
        base += 25.0
    if proxy.dns_over_https_ok:
        base += 10.0
    hist = history.get(proxy.id) or {}
    base += hist.get("success_rate", 0.0) * 15.0
    base += _latency_points(proxy.latency_ms, settings.LAT_SOFT_CAP_MS, 15.0)
    return round(base, 2)


def score_stability(
    proxy: Proxy, history: Mapping[str, Mapping[str, float]], settings: AppSettings
) -> float:
    """Legacy scoring function prioritizing stability."""
    hist = history.get(proxy.id) or {}
    score = hist.get("success_rate", 0.0) * 50.0
    score += hist.get("latency_ewma", 0.0) * 20.0
    score += _latency_points(proxy.latency_ms, settings.LAT_SOFT_CAP_MS, 30.0)
    return round(score, 2)
