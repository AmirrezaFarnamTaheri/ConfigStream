from unittest.mock import MagicMock

import pytest

from configstream.config import AppSettings
from configstream.models import Proxy
from configstream.score import (_latency_points, calculate_health_score,
                                score_balanced, score_privacy, score_speed,
                                score_stability)


class TestScore:
    @pytest.fixture
    def mock_proxy(self):
        proxy = MagicMock(spec=Proxy)
        proxy.id = "test_proxy"
        proxy.latency = 100
        proxy.latency_ms = 100
        proxy.is_working = True
        proxy.details = {"tls": True, "aead": True, "encryption": True}
        proxy.dns_over_https_ok = True
        proxy.throughput_kbps = 2500
        proxy.age_seconds = 43200  # 12 hours
        return proxy

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock(spec=AppSettings)
        settings.SCORE_WEIGHTS = {
            "historical_success": 40.0,
            "latency": 30.0,
            "security": 20.0,
            "current_status": 10.0,
        }
        settings.LAT_SOFT_CAP_MS = 500
        return settings

    @pytest.fixture
    def mock_history(self):
        return {"test_proxy": {"success_rate": 0.9, "latency_ewma": 0.8}}

    def test_latency_points(self):
        # Test low latency (good)
        points = _latency_points(10, 500, 30)
        assert points > 20

        # Test high latency (bad)
        points_bad = _latency_points(2000, 500, 30)
        assert points_bad < 10

        # Test None
        assert _latency_points(None, 500, 30) == 0.0

        # Test 0 cap
        assert _latency_points(100, 0, 30) == 0.0

    def test_calculate_health_score_full(self, mock_proxy, mock_settings):
        # Mock cache
        mock_cache = MagicMock()
        mock_cache.get_health_score.return_value = 0.8  # 80% success

        score = calculate_health_score(mock_proxy, mock_cache, mock_settings)

        # Expected:
        # History: 0.8 * 40 = 32
        # Latency: ~30 (low latency)
        # Security: 20 (all features)
        # Status: 10
        # Total: ~92
        assert 80 < score <= 100

    def test_calculate_health_score_no_cache_no_latency(
        self, mock_proxy, mock_settings
    ):
        mock_proxy.latency = None
        score = calculate_health_score(mock_proxy, None, mock_settings)
        # History: 0.5 * 40 = 20
        # Latency: 0.5 * 30 = 15
        # Security: 20
        # Status: 10
        # Total: 65
        assert score == 65.0

    def test_legacy_scoring(self, mock_proxy, mock_history, mock_settings):
        # Just verify they run and return float
        assert isinstance(score_speed(mock_proxy, mock_history, mock_settings), float)
        assert isinstance(
            score_balanced(mock_proxy, mock_history, mock_settings), float
        )
        assert isinstance(score_privacy(mock_proxy, mock_history, mock_settings), float)
        assert isinstance(
            score_stability(mock_proxy, mock_history, mock_settings), float
        )
