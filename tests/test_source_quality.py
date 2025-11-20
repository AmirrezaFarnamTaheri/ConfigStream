import pytest
from configstream.source_quality import calculate_diversity_score
from configstream.models import Proxy


def test_diversity_score_empty():
    assert calculate_diversity_score([]) == 0.0


def test_diversity_score_single_country():
    proxies = [
        Proxy(
            config="...", protocol="http", address="1.1.1.1", port=80, country_code="US"
        )
        for _ in range(10)
    ]
    # All same country -> 0 diversity
    assert calculate_diversity_score(proxies) == 0.0


def test_diversity_score_high():
    proxies = [
        Proxy(
            config="...", protocol="http", address="1.1.1.1", port=80, country_code="US"
        ),
        Proxy(
            config="...", protocol="http", address="1.1.1.1", port=80, country_code="DE"
        ),
        Proxy(
            config="...", protocol="http", address="1.1.1.1", port=80, country_code="JP"
        ),
        Proxy(
            config="...", protocol="http", address="1.1.1.1", port=80, country_code="FR"
        ),
    ]
    # 4 distinct countries, perfectly distributed
    # 1 - (0.25^2 * 4) = 1 - 0.25 = 0.75
    assert calculate_diversity_score(proxies) == 0.75
