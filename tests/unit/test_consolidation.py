import pytest
from configstream.models import Proxy
from configstream.consolidation import (
    calculate_compound_score,
    rank_and_rename_proxies,
    select_top_configs,
    get_country_flag,
)


@pytest.fixture
def sample_proxies():
    return [
        Proxy(
            config="vmess://1",
            protocol="vmess",
            address="1.1.1.1",
            port=443,
            latency=100,
            country_code="US",
            is_working=True,
        ),
        Proxy(
            config="vmess://2",
            protocol="vmess",
            address="1.1.1.2",
            port=443,
            latency=50,  # Better latency
            country_code="US",
            is_working=True,
        ),
        Proxy(
            config="ss://1",
            protocol="shadowsocks",
            address="2.2.2.1",
            port=8388,
            latency=200,
            country_code="DE",
            is_working=True,
        ),
        Proxy(
            config="vmess://3",
            protocol="vmess",
            address="1.1.1.3",
            port=443,
            latency=None,  # No latency
            country_code="JP",
            is_working=True,
        ),
    ]


def test_calculate_compound_score():
    p = Proxy(config="test", protocol="vmess", address="1.1.1.1", port=443, latency=100)
    assert calculate_compound_score(p) == 100.0

    p_stale = Proxy(
        config="test",
        protocol="vmess",
        address="1.1.1.1",
        port=443,
        latency=100,
        stale=True,
    )
    assert calculate_compound_score(p_stale) == 150.0  # 100 * 1.5

    p_none = Proxy(
        config="test", protocol="vmess", address="1.1.1.1", port=443, latency=None
    )
    assert calculate_compound_score(p_none) == 5000.0  # Default


def test_get_country_flag():
    assert get_country_flag("US") == "🇺🇸"
    assert get_country_flag("de") == "🇩🇪"
    assert get_country_flag("XX") == "🌍"
    assert get_country_flag(None) == "🌍"


def test_rank_and_rename_proxies(sample_proxies):
    ranked = rank_and_rename_proxies(sample_proxies)
    assert len(ranked) == 4

    # Check sorting order for vmess (latency 50 -> 100 -> None)
    vmess_proxies = [p for p in ranked if p.protocol == "vmess"]
    assert vmess_proxies[0].latency == 50
    assert "VMESS-1" in vmess_proxies[0].remarks
    assert vmess_proxies[1].latency == 100
    assert "VMESS-2" in vmess_proxies[1].remarks
    assert vmess_proxies[2].latency is None
    assert "VMESS-3" in vmess_proxies[2].remarks

    # Check SS
    ss_proxies = [p for p in ranked if p.protocol == "shadowsocks"]
    assert len(ss_proxies) == 1
    assert "SHADOWSOCKS-1" in ss_proxies[0].remarks


def test_select_top_configs(sample_proxies):
    # Limit top per protocol to 1, total to 2
    # Should pick:
    # 1. Best VMess (latency 50)
    # 2. Best SS (latency 200)
    # Total 2 selected.

    selected = select_top_configs(sample_proxies, top_per_protocol=1, total_limit=2)

    assert len(selected) == 2
    assert selected[0].protocol == "vmess"
    assert selected[0].latency == 50
    assert selected[1].protocol == "shadowsocks"

    # Test filling from overall
    # Limit top per protocol 1, total 100
    # Should pick:
    # 1. Best VMess
    # 2. Best SS
    # 3. Next best VMess (from overall fill)
    # 4. Last VMess (from overall fill)

    selected_all = select_top_configs(
        sample_proxies, top_per_protocol=1, total_limit=100
    )
    assert len(selected_all) == 4

    # Verify uniqueness logic
    dupe_proxies = sample_proxies + [sample_proxies[0]]  # Add duplicate
    selected_dupe = select_top_configs(
        dupe_proxies, top_per_protocol=10, total_limit=100
    )
    assert len(selected_dupe) == 4  # Duplicate should be ignored
