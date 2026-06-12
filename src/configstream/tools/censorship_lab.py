# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Censorship Lab: Simulates various censorship scenarios for testing evasion techniques.

This module provides fault injection capabilities to test how proxies behave
under different censorship conditions (DNS poisoning, IP blocking, UDP drops, etc.).
"""

import asyncio
import logging
from secrets import choice as secure_choice
from typing import List, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class CensorshipMode(Enum):
    """Censorship simulation modes."""

    DNS_POISON = "dns_poison"
    IP_BLOCK = "ip_block"
    UDP_BLOCK = "udp_block"
    SLOW_DNS = "slow_dns"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"


class PoisonedDNSResolver:
    """Test resolver that returns poisoned IPs, NXDOMAIN, or slow replies."""

    def __init__(
        self,
        poison_ips: Optional[List[str]] = None,
        nxdomain_domains: Optional[List[str]] = None,
        slow_domains: Optional[List[str]] = None,
        slow_delay: float = 5.0,
    ):
        self.poison_ips = poison_ips or ["127.0.0.1", "127.0.0.1"]
        self.nxdomain_domains = nxdomain_domains or []
        self.slow_domains = slow_domains or []
        self.slow_delay = slow_delay

    async def resolve(self, hostname: str) -> Optional[str]:
        """Resolve hostname with poisoning logic."""
        hostname_lower = hostname.lower()

        # NXDOMAIN simulation
        if any(domain in hostname_lower for domain in self.nxdomain_domains):
            logger.debug(f"[PoisonedDNS] NXDOMAIN for {hostname}")
            return None

        # Slow DNS simulation
        if any(domain in hostname_lower for domain in self.slow_domains):
            await asyncio.sleep(self.slow_delay)
            logger.debug(f"[PoisonedDNS] Slow reply for {hostname}")

        # Return poisoned IP
        return secure_choice(self.poison_ips)


class IPBlocklist:
    """Mock IP blocklist for testing."""

    def __init__(
        self,
        blocked_ips: Optional[List[str]] = None,
        blocked_asns: Optional[List[int]] = None,
        blocked_ranges: Optional[List[str]] = None,
    ):
        self.blocked_ips = set(blocked_ips or [])
        self.blocked_asns = set(blocked_asns or [])
        self.blocked_ranges = blocked_ranges or []

    def is_blocked(self, ip: str, asn: Optional[int] = None) -> bool:
        """Check if IP/ASN is blocked."""
        if ip in self.blocked_ips:
            return True
        if asn and asn in self.blocked_asns:
            return True
        # Check CIDR ranges
        try:
            import ipaddress

            ip_addr = ipaddress.ip_address(ip)
            for cidr in self.blocked_ranges:
                if ip_addr in ipaddress.ip_network(cidr, strict=False):
                    return True
        except (ValueError, TypeError):
            pass
        return False


class CensorshipLab:
    """Main censorship simulation harness."""

    def __init__(self):
        self.poisoned_resolver: Optional[PoisonedDNSResolver] = None
        self.ip_blocklist: Optional[IPBlocklist] = None
        self.active_modes: List[CensorshipMode] = []
        self.timeout_multiplier: float = 1.0
        self.rate_limit_threshold: int = 10
        self.rate_limit_window: float = 60.0

    def configure_mode(
        self,
        mode: CensorshipMode,
        **kwargs: Any,
    ) -> None:
        """Configure a censorship mode."""
        if mode == CensorshipMode.DNS_POISON:
            self.poisoned_resolver = PoisonedDNSResolver(
                poison_ips=kwargs.get("poison_ips"),
                nxdomain_domains=kwargs.get("nxdomain_domains"),
                slow_domains=kwargs.get("slow_domains"),
                slow_delay=kwargs.get("slow_delay", 5.0),
            )
            self.active_modes.append(mode)
            logger.info("[CensorshipLab] Enabled DNS poisoning mode")

        elif mode == CensorshipMode.IP_BLOCK:
            self.ip_blocklist = IPBlocklist(
                blocked_ips=kwargs.get("blocked_ips"),
                blocked_asns=kwargs.get("blocked_asns"),
                blocked_ranges=kwargs.get("blocked_ranges"),
            )
            self.active_modes.append(mode)
            logger.info("[CensorshipLab] Enabled IP blocking mode")

        elif mode == CensorshipMode.SLOW_DNS:
            if not self.poisoned_resolver:
                self.poisoned_resolver = PoisonedDNSResolver()
            self.poisoned_resolver.slow_delay = kwargs.get("slow_delay", 5.0)
            self.active_modes.append(mode)
            logger.info("[CensorshipLab] Enabled slow DNS mode")

        elif mode == CensorshipMode.TIMEOUT:
            self.timeout_multiplier = kwargs.get("multiplier", 10.0)
            self.active_modes.append(mode)
            logger.info(
                f"[CensorshipLab] Enabled timeout simulation (x{self.timeout_multiplier})"
            )

        elif mode == CensorshipMode.RATE_LIMIT:
            self.rate_limit_threshold = kwargs.get("threshold", 10)
            self.rate_limit_window = kwargs.get("window", 60.0)
            self.active_modes.append(mode)
            logger.info(
                f"[CensorshipLab] Enabled rate limiting ({self.rate_limit_threshold} req/{self.rate_limit_window}s)"
            )

    async def simulate_dns_resolve(self, hostname: str) -> Optional[str]:
        """Simulate DNS resolution with poisoning."""
        if CensorshipMode.DNS_POISON in self.active_modes and self.poisoned_resolver:
            return await self.poisoned_resolver.resolve(hostname)
        return None

    def check_ip_blocked(self, ip: str, asn: Optional[int] = None) -> bool:
        """Check if IP is blocked."""
        if CensorshipMode.IP_BLOCK in self.active_modes and self.ip_blocklist:
            return self.ip_blocklist.is_blocked(ip, asn)
        return False

    def apply_timeout(self, base_timeout: float) -> float:
        """Apply timeout multiplier."""
        if CensorshipMode.TIMEOUT in self.active_modes:
            return base_timeout * self.timeout_multiplier
        return base_timeout

    def should_drop_udp(self) -> bool:
        """Check if UDP should be dropped."""
        return CensorshipMode.UDP_BLOCK in self.active_modes

    def reset(self) -> None:
        """Reset all censorship modes."""
        self.poisoned_resolver = None
        self.ip_blocklist = None
        self.active_modes.clear()
        self.timeout_multiplier = 1.0
        logger.info("[CensorshipLab] Reset all censorship modes")


# Global instance for testing
_lab_instance: Optional[CensorshipLab] = None


def get_censorship_lab() -> CensorshipLab:
    """Get or create the global censorship lab instance."""
    global _lab_instance
    if _lab_instance is None:
        _lab_instance = CensorshipLab()
    return _lab_instance


async def run_censorship_test(
    mode: str,
    test_func: Callable,
    **kwargs: Any,
) -> Any:
    """
    Run a test function under a specific censorship mode.

    Args:
        mode: Censorship mode (dns_poison, ip_block, udp_block, slow_dns, timeout, rate_limit)
        test_func: Async test function to run
        **kwargs: Configuration for the censorship mode

    Returns:
        Result from test_func
    """
    lab = get_censorship_lab()
    try:
        censorship_mode = CensorshipMode(mode)
        lab.configure_mode(censorship_mode, **kwargs)
        result = await test_func()
        return result
    finally:
        lab.reset()
