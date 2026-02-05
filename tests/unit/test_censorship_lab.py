# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for censorship lab."""

import pytest
import asyncio
from configstream.tools.censorship_lab import (
    CensorshipLab,
    CensorshipMode,
    PoisonedDNSResolver,
    IPBlocklist,
    get_censorship_lab,
    run_censorship_test,
)


class TestPoisonedDNSResolver:
    """Test poisoned DNS resolver."""

    @pytest.mark.asyncio
    async def test_resolve_poisoned_ip(self):
        """Test resolving with poisoned IP."""
        resolver = PoisonedDNSResolver(poison_ips=["127.0.0.1"])
        result = await resolver.resolve("example.com")
        assert result == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_resolve_nxdomain(self):
        """Test NXDOMAIN simulation."""
        resolver = PoisonedDNSResolver(
            nxdomain_domains=["blocked.com"]
        )
        result = await resolver.resolve("blocked.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_slow_dns(self):
        """Test slow DNS simulation."""
        resolver = PoisonedDNSResolver(
            slow_domains=["slow.com"],
            slow_delay=0.1,
        )
        import time
        start = time.time()
        result = await resolver.resolve("slow.com")
        elapsed = time.time() - start
        assert elapsed >= 0.1
        assert result in resolver.poison_ips


class TestIPBlocklist:
    """Test IP blocklist."""

    def test_is_blocked_ip(self):
        """Test IP blocking."""
        blocklist = IPBlocklist(blocked_ips=["1.2.3.4", "5.6.7.8"])
        assert blocklist.is_blocked("1.2.3.4") is True
        assert blocklist.is_blocked("9.9.9.9") is False

    def test_is_blocked_asn(self):
        """Test ASN blocking."""
        blocklist = IPBlocklist(blocked_asns=[15169, 13335])
        assert blocklist.is_blocked("8.8.8.8", asn=15169) is True
        assert blocklist.is_blocked("8.8.8.8", asn=12345) is False


class TestCensorshipLab:
    """Test censorship lab."""

    def test_configure_dns_poison(self):
        """Test DNS poisoning mode."""
        lab = CensorshipLab()
        lab.configure_mode(
            CensorshipMode.DNS_POISON,
            poison_ips=["127.0.0.1"],
            nxdomain_domains=["blocked.com"],
        )
        assert CensorshipMode.DNS_POISON in lab.active_modes
        assert lab.poisoned_resolver is not None

    def test_configure_ip_block(self):
        """Test IP blocking mode."""
        lab = CensorshipLab()
        lab.configure_mode(
            CensorshipMode.IP_BLOCK,
            blocked_ips=["1.2.3.4"],
            blocked_asns=[15169],
        )
        assert CensorshipMode.IP_BLOCK in lab.active_modes
        assert lab.ip_blocklist is not None

    def test_configure_slow_dns(self):
        """Test slow DNS mode."""
        lab = CensorshipLab()
        lab.configure_mode(
            CensorshipMode.SLOW_DNS,
            slow_delay=5.0,
        )
        assert CensorshipMode.SLOW_DNS in lab.active_modes

    def test_configure_timeout(self):
        """Test timeout simulation mode."""
        lab = CensorshipLab()
        lab.configure_mode(
            CensorshipMode.TIMEOUT,
            multiplier=10.0,
        )
        assert CensorshipMode.TIMEOUT in lab.active_modes
        assert lab.timeout_multiplier == 10.0

    def test_configure_rate_limit(self):
        """Test rate limiting mode."""
        lab = CensorshipLab()
        lab.configure_mode(
            CensorshipMode.RATE_LIMIT,
            threshold=10,
            window=60.0,
        )
        assert CensorshipMode.RATE_LIMIT in lab.active_modes
        assert lab.rate_limit_threshold == 10

    def test_check_ip_blocked(self):
        """Test IP blocking check."""
        lab = CensorshipLab()
        lab.configure_mode(
            CensorshipMode.IP_BLOCK,
            blocked_ips=["1.2.3.4"],
        )
        assert lab.check_ip_blocked("1.2.3.4") is True
        assert lab.check_ip_blocked("9.9.9.9") is False

    def test_apply_timeout(self):
        """Test timeout application."""
        lab = CensorshipLab()
        lab.configure_mode(
            CensorshipMode.TIMEOUT,
            multiplier=2.0,
        )
        result = lab.apply_timeout(5.0)
        assert result == 10.0

    def test_reset(self):
        """Test lab reset."""
        lab = CensorshipLab()
        lab.configure_mode(CensorshipMode.DNS_POISON)
        lab.reset()
        assert len(lab.active_modes) == 0
        assert lab.poisoned_resolver is None


class TestCensorshipLabIntegration:
    """Integration tests for censorship lab."""

    @pytest.mark.asyncio
    async def test_simulate_dns_resolve(self):
        """Test DNS resolution simulation."""
        lab = CensorshipLab()
        lab.configure_mode(
            CensorshipMode.DNS_POISON,
            poison_ips=["127.0.0.1"],
        )
        result = await lab.simulate_dns_resolve("example.com")
        assert result == "127.0.0.1"

    def test_get_censorship_lab_singleton(self):
        """Test singleton pattern."""
        lab1 = get_censorship_lab()
        lab2 = get_censorship_lab()
        assert lab1 is lab2

    @pytest.mark.asyncio
    async def test_run_censorship_test(self):
        """Test running test under censorship mode."""
        async def test_func():
            return "success"

        result = await run_censorship_test(
            "dns_poison",
            test_func,
            poison_ips=["127.0.0.1"],
        )
        assert result == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

