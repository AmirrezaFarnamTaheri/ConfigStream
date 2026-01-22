# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock
from configstream.cache_warming import warm_cache, get_cache_warming_strategy
from configstream.models import Proxy


@pytest.fixture
def mock_cache():
    cache = MagicMock()
    # Mock get method to return True for some proxies, False for others
    cache.get = MagicMock()
    cache.get_health_score = MagicMock()
    return cache


def create_proxy(id, latency=100):
    p = MagicMock(spec=Proxy)
    p.id = id  # Assuming models.Proxy has id or is hashable
    p.latency = latency
    return p


def test_warm_cache(mock_cache):
    p1 = create_proxy("p1")
    p2 = create_proxy("p2")  # uncached
    p3 = create_proxy("p3")  # cached, low score
    p4 = create_proxy("p4")  # cached, high score

    proxies = [p1, p2, p3, p4]

    # Setup cache behavior
    mock_cache.get.side_effect = lambda p: p.id in ["p1", "p3", "p4"]

    # health scores
    def health_score(p):
        if p.id == "p1":
            return 0.8
        if p.id == "p4":
            return 0.9
        if p.id == "p3":
            return 0.5
        return 0

    mock_cache.get_health_score.side_effect = health_score

    result = warm_cache(mock_cache, proxies)

    # Expected order:
    # 1. High score (>0.7): p4 (0.9), p1 (0.8)
    # 2. Uncached: p2
    # 3. Low score: p3 (0.5)

    assert result[0].id == "p4"
    assert result[1].id == "p1"
    assert result[2].id == "p2"
    assert result[3].id == "p3"


def test_warm_cache_all_uncached(mock_cache):
    p1 = create_proxy("p1")
    p2 = create_proxy("p2")
    proxies = [p1, p2]
    mock_cache.get.return_value = False

    result = warm_cache(mock_cache, proxies)
    assert len(result) == 2
    assert set([p.id for p in result]) == {"p1", "p2"}


def test_get_cache_warming_strategy():
    s1 = get_cache_warming_strategy(50)
    assert s1["priority_test_count"] == 50
    assert s1["batch_size"] == 50

    s2 = get_cache_warming_strategy(500)
    assert s2["priority_test_count"] == 100
    assert s2["batch_size"] == 100

    s3 = get_cache_warming_strategy(2000)
    assert s3["priority_test_count"] == 200
    assert s3["batch_size"] == 200
