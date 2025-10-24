"""Tests for proxy health scoring system."""

import pytest

from configstream.config import AppSettings
from configstream.models import Proxy
from configstream.score import calculate_health_score, _latency_points


@pytest.fixture
def sample_proxy():
    """Create sample proxy for testing."""
    return Proxy(
        config="vmess://test",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        is_working=True,
        latency=100.0,
        details={"tls": True, "aead": True},
    )


def test_latency_points():
    """Test latency points calculation."""
    settings = AppSettings()

    # Low latency should give high points
    points = _latency_points(100.0, settings.LAT_SOFT_CAP_MS, 30.0)
    assert points > 15.0  # Should be above midpoint

    # High latency should give low points
    points = _latency_points(5000.0, settings.LAT_SOFT_CAP_MS, 30.0)
    assert points < 5.0

    # None latency should give 0
    points = _latency_points(None, settings.LAT_SOFT_CAP_MS, 30.0)
    assert points == 0.0


def test_calculate_health_score_basic(sample_proxy):
    """Test basic health score calculation."""
    score = calculate_health_score(sample_proxy)

    # Working proxy with good latency should score well
    assert 50.0 < score <= 100.0


def test_calculate_health_score_not_working():
    """Test scoring of non-working proxy."""
    proxy = Proxy(
        config="test",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        is_working=False,
        latency=None,
    )

    score = calculate_health_score(proxy)

    # Non-working proxy should score lower
    assert score < 50.0


def test_calculate_health_score_with_security():
    """Test scoring considers security features."""
    # Proxy with TLS
    proxy_with_tls = Proxy(
        config="test",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        is_working=True,
        latency=100.0,
        details={"tls": True},
    )

    # Proxy without TLS
    proxy_without_tls = Proxy(
        config="test",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        is_working=True,
        latency=100.0,
        details={},
    )

    score_with_tls = calculate_health_score(proxy_with_tls)
    score_without_tls = calculate_health_score(proxy_without_tls)

    # TLS proxy should score higher
    assert score_with_tls > score_without_tls


def test_calculate_health_score_bounds():
    """Test score is bounded between 0 and 100."""
    # Best possible proxy
    best_proxy = Proxy(
        config="test",
        protocol="vmess",
        address="1.2.3.4",
        port=443,
        is_working=True,
        latency=10.0,
        details={"tls": True, "aead": True, "encryption": True},
        dns_over_https_ok=True,
    )

    score = calculate_health_score(best_proxy)
    assert 0.0 <= score <= 100.0

    # Worst possible proxy
    worst_proxy = Proxy(
        config="test",
        protocol="http",
        address="1.2.3.4",
        port=80,
        is_working=False,
        latency=None,
        details={},
    )

    score = calculate_health_score(worst_proxy)
    assert 0.0 <= score <= 100.0


def test_legacy_score_speed(sample_proxy):
    """Test legacy speed scoring function."""
    from configstream.score import score_speed

    settings = AppSettings()
    history = {}

    score = score_speed(sample_proxy, history, settings)

    assert isinstance(score, float)
    assert score >= 0.0


def test_legacy_score_balanced(sample_proxy):
    """Test legacy balanced scoring function."""
    from configstream.score import score_balanced

    settings = AppSettings()
    history = {}

    score = score_balanced(sample_proxy, history, settings)

    assert isinstance(score, float)
    assert score >= 0.0


def test_legacy_score_privacy(sample_proxy):
    """Test legacy privacy scoring function."""
    from configstream.score import score_privacy

    settings = AppSettings()
    history = {}

    score = score_privacy(sample_proxy, history, settings)

    assert isinstance(score, float)
    assert score >= 0.0


def test_legacy_score_stability(sample_proxy):
    """Test legacy stability scoring function."""
    from configstream.score import score_stability

    settings = AppSettings()
    history = {
        sample_proxy.id: {
            "success_rate": 0.8,
            "latency_ewma": 0.5,
        }
    }

    score = score_stability(sample_proxy, history, settings)

    assert isinstance(score, float)
    assert score > 0.0
