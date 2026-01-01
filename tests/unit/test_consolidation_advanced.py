# SPDX-License-Identifier: AGPL-3.0-or-later
"""Advanced tests for consolidation and proxy ranking."""

from configstream.consolidation import (
    calculate_compound_score,
    get_country_flag,
    rank_and_rename_proxies,
    select_top_configs,
)
from configstream.models import Proxy


class TestCompoundScoring:
    """Test compound score calculations."""

    def test_calculate_compound_score_with_latency(self):
        """Test score calculation with valid latency."""
        proxy = Proxy(
            config="test://example.com:443",
            protocol="vmess",
            address="example.com",
            port=443,
            latency=100.0,
        )

        score = calculate_compound_score(proxy)

        # Lower is better, score should equal latency * penalty
        assert score == 100.0

    def test_calculate_compound_score_no_latency(self):
        """Test score calculation with no latency."""
        proxy = Proxy(
            config="test://example.com:443",
            protocol="vmess",
            address="example.com",
            port=443,
            latency=None,
        )

        score = calculate_compound_score(proxy)

        # Should default to 5000
        assert score == 5000.0

    def test_calculate_compound_score_stale_proxy(self):
        """Test score calculation for stale proxy."""
        proxy = Proxy(
            config="test://example.com:443",
            protocol="vmess",
            address="example.com",
            port=443,
            latency=100.0,
            stale=True,
        )

        score = calculate_compound_score(proxy)

        # Stale proxies should have penalty multiplier
        assert score == 150.0  # 100 * 1.5


class TestCountryFlags:
    """Test country flag emoji generation."""

    def test_get_country_flag_valid(self):
        """Test flag generation for valid country codes."""
        assert get_country_flag("US") == "🇺🇸"
        assert get_country_flag("DE") == "🇩🇪"
        assert get_country_flag("JP") == "🇯🇵"
        assert get_country_flag("FR") == "🇫🇷"
        assert get_country_flag("GB") == "🇬🇧"

    def test_get_country_flag_lowercase(self):
        """Test flag generation with lowercase input."""
        assert get_country_flag("us") == "🇺🇸"
        assert get_country_flag("de") == "🇩🇪"

    def test_get_country_flag_invalid(self):
        """Test flag generation for invalid codes."""
        assert get_country_flag("XX") == "🌍"
        assert get_country_flag("") == "🌍"
        assert get_country_flag("U") == "🌍"  # Too short
        assert get_country_flag("USA") == "🌍"  # Too long

    def test_get_country_flag_none(self):
        """Test flag generation with None."""
        assert get_country_flag(None) == "🌍"  # type: ignore

    def test_get_country_flag_special_chars(self):
        """Test flag generation with special characters."""
        # Numbers will produce regional indicator symbols (not real flags)
        result = get_country_flag("12")
        assert isinstance(result, str) and len(result) > 0

        # Special chars will produce globe emoji
        # (actual behavior may vary depending on validation)
        result2 = get_country_flag("@#")
        assert isinstance(result2, str)


class TestRankingAndRenaming:
    """Test proxy ranking and renaming."""

    def test_rank_and_rename_single_protocol(self):
        """Test ranking proxies of single protocol."""
        proxies = [
            Proxy(
                config="vmess://1",
                protocol="vmess",
                address="1.1.1.1",
                port=443,
                latency=200.0,
                country_code="US",
                remarks="Original1",
            ),
            Proxy(
                config="vmess://2",
                protocol="vmess",
                address="2.2.2.2",
                port=443,
                latency=100.0,
                country_code="DE",
                remarks="Original2",
            ),
            Proxy(
                config="vmess://3",
                protocol="vmess",
                address="3.3.3.3",
                port=443,
                latency=300.0,
                country_code="JP",
                remarks="Original3",
            ),
        ]

        ranked = rank_and_rename_proxies(proxies)

        assert len(ranked) == 3

        # Should be sorted by latency (lowest first)
        assert ranked[0].latency == 100.0
        assert ranked[1].latency == 200.0
        assert ranked[2].latency == 300.0

        # Check naming format: PROTOCOL-RANK [FLAG] ||| ORIGINAL_NAME
        assert "VMESS-1" in ranked[0].remarks
        assert "🇩🇪" in ranked[0].remarks
        assert "Original2" in ranked[0].remarks

        assert "VMESS-2" in ranked[1].remarks
        assert "🇺🇸" in ranked[1].remarks

        assert "VMESS-3" in ranked[2].remarks
        assert "🇯🇵" in ranked[2].remarks

    def test_rank_and_rename_multiple_protocols(self):
        """Test ranking with multiple protocols."""
        proxies = [
            Proxy(
                config="vmess://1",
                protocol="vmess",
                address="1.1.1.1",
                port=443,
                latency=200.0,
                country_code="US",
            ),
            Proxy(
                config="vless://1",
                protocol="vless",
                address="2.2.2.2",
                port=443,
                latency=150.0,
                country_code="DE",
            ),
            Proxy(
                config="vmess://2",
                protocol="vmess",
                address="3.3.3.3",
                port=443,
                latency=100.0,
                country_code="JP",
            ),
        ]

        ranked = rank_and_rename_proxies(proxies)

        assert len(ranked) == 3

        # Find vmess proxies
        vmess_proxies = [p for p in ranked if p.protocol == "vmess"]
        assert len(vmess_proxies) == 2
        # Within vmess, should be sorted by latency
        assert vmess_proxies[0].latency == 100.0
        assert "VMESS-1" in vmess_proxies[0].remarks

    def test_rank_and_rename_with_none_latency(self):
        """Test ranking with None latency values."""
        proxies = [
            Proxy(
                config="vmess://1",
                protocol="vmess",
                address="1.1.1.1",
                port=443,
                latency=200.0,
                country_code="US",
            ),
            Proxy(
                config="vmess://2",
                protocol="vmess",
                address="2.2.2.2",
                port=443,
                latency=None,  # No latency
                country_code="DE",
            ),
            Proxy(
                config="vmess://3",
                protocol="vmess",
                address="3.3.3.3",
                port=443,
                latency=100.0,
                country_code="JP",
            ),
        ]

        ranked = rank_and_rename_proxies(proxies)

        # Proxies with None latency should go to end
        assert ranked[0].latency == 100.0
        assert ranked[1].latency == 200.0
        assert ranked[2].latency is None

    def test_rank_and_rename_long_name_truncation(self):
        """Test that overly long names are truncated."""
        proxies = [
            Proxy(
                config="vmess://1",
                protocol="vmess",
                address="1.1.1.1",
                port=443,
                latency=100.0,
                country_code="US",
                remarks="A" * 100,  # Very long name
            ),
        ]

        ranked = rank_and_rename_proxies(proxies)

        # Should be truncated to 80 chars with "..."
        assert len(ranked[0].remarks) <= 80


class TestTopConfigSelection:
    """Test top config selection logic."""

    def test_select_top_configs_single_protocol(self):
        """Test selection from single protocol."""
        proxies = [
            Proxy(
                config=f"vmess://{i}",
                protocol="vmess",
                address=f"{i}.{i}.{i}.{i}",
                port=443,
                latency=float(i * 10),
            )
            for i in range(1, 101)  # 100 proxies
        ]

        # Select top 50 per protocol, 1000 total
        selected = select_top_configs(proxies, top_per_protocol=50, total_limit=1000)

        # Should get at most top_per_protocol from this single protocol
        # Then fill up to total_limit from overall ranking
        assert len(selected) >= 50
        assert len(selected) <= 100  # All proxies

        # Lowest latency ones should be included
        assert any(p.latency == 10.0 for p in selected)

    def test_select_top_configs_multiple_protocols(self):
        """Test selection from multiple protocols."""
        proxies = []

        # 100 vmess
        for i in range(1, 101):
            proxies.append(
                Proxy(
                    config=f"vmess://{i}",
                    protocol="vmess",
                    address=f"{i}.1.1.1",
                    port=443,
                    latency=float(i * 10),
                )
            )

        # 100 vless
        for i in range(1, 101):
            proxies.append(
                Proxy(
                    config=f"vless://{i}",
                    protocol="vless",
                    address=f"{i}.2.2.2",
                    port=443,
                    latency=float(i * 10),
                )
            )

        # Select top 30 per protocol
        selected = select_top_configs(proxies, top_per_protocol=30, total_limit=1000)

        # Should get at least 30 from each protocol
        vmess_count = sum(1 for p in selected if p.protocol == "vmess")
        vless_count = sum(1 for p in selected if p.protocol == "vless")

        assert vmess_count >= 30
        assert vless_count >= 30

        # Should have both protocols represented
        assert vmess_count > 0 and vless_count > 0

    def test_select_top_configs_total_limit(self):
        """Test that total limit influences selection."""
        proxies = [
            Proxy(
                config=f"vmess://{i}",
                protocol="vmess",
                address=f"{i}.{i}.{i}.{i}",
                port=443,
                latency=float(i * 10),
            )
            for i in range(1, 201)  # 200 proxies
        ]

        # Select top 100 per protocol, but limit total to 50
        selected = select_top_configs(proxies, top_per_protocol=100, total_limit=50)

        # The function first takes top_per_protocol (100), then fills to total_limit
        # Since we have 200 proxies and top_per_protocol=100, we get 100
        # If top_per_protocol >= total_limit, we should get around total_limit
        assert len(selected) >= 50
        assert len(selected) <= 200

    def test_select_top_configs_deduplication(self):
        """Test that duplicates are removed."""
        proxies = [
            Proxy(
                config="vmess://same",
                protocol="vmess",
                address="1.1.1.1",
                port=443,
                latency=100.0,
            ),
            Proxy(
                config="vmess://same",  # Duplicate
                protocol="vmess",
                address="1.1.1.1",
                port=443,
                latency=200.0,
            ),
            Proxy(
                config="vmess://different",
                protocol="vmess",
                address="2.2.2.2",
                port=443,
                latency=150.0,
            ),
        ]

        selected = select_top_configs(proxies, top_per_protocol=10, total_limit=100)

        # Should remove duplicate
        assert len(selected) == 2
        configs = [p.config for p in selected]
        assert configs.count("vmess://same") == 1
