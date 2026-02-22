# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import threading

__all__ = ["PipelineStats", "PipelineResult"]


@dataclass
class PipelineStats:
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    drop_reasons: Dict[str, int] = field(default_factory=dict)

    # Internal lock for thread-safe access to dictionary fields
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # Canonical Stats
    total_configured_sources: int = 0
    fetched_sources: int = 0
    fetched_lines: int = 0
    total_lines_sourced: int = 0  # Raw lines fetched from all sources
    parsed: int = 0
    total_unique_candidates: int = 0 # Parsed proxies before testing
    tested: int = 0
    total_tested: int = 0
    working: int = 0
    total_working: int = 0
    total_valid_proxies: int = 0 # Working proxies after testing
    total_proxies: int = 0 # Working + smart chains
    total_clean: int = 0 # Working minus revived
    total_dirty: int = 0 # Honeypots + dirty IPs blocked
    geo_resolved: int = 0
    duration: float = 0.0
    duration_seconds: float = 0.0
    final_count: int = 0
    cache_misses: int = 0
    success_rate: float = 0.0

    # Intelligence Layer Stats
    scanner_ips_found: int = 0
    washer_success_count: int = 0
    smart_chain_count: int = 0
    total_smart_chains: int = 0
    chain_outbounds_count: int = 0
    # Time budget handling
    time_limited: bool = False
    time_limit_seconds: int = 0
    chosen_subset_size: int = 0

    # Revived Stats
    revived_warp: int = 0
    revived_vwarp: int = 0
    total_revived: int = 0
    shielded_count: int = 0  # Proxies resurrected via shielding (Copper to Gold)

    # Evasion Metrics
    evasion_utls_enabled: int = 0  # Proxies with uTLS fingerprint rotation
    evasion_alpn_enabled: int = 0  # Proxies with ALPN rotation
    evasion_fragmentation_enabled: int = 0  # Always 0; sing-box removed tls_fragment
    evasion_multiplexing_enabled: int = 0  # Proxies with multiplexing
    evasion_dns_safe_count: int = 0  # Proxies in DNS-safe outputs
    evasion_dns_hardened_count: int = 0  # Proxies in DNS-hardened outputs

    # Vwarp Stats (Efficiency of Vwarp Tool specifically)
    warp_attempts: int = 0  # Standard WARP attempts
    vwarp_attempts: int = 0
    vwarp_success: int = 0

    # Washing Enabled Flag
    washing_enabled: bool = True

    # Detailed Stats
    protocols: Dict[str, int] = field(default_factory=dict)
    country_stats: Dict[str, int] = field(default_factory=dict)
    asns: Dict[str, int] = field(default_factory=dict)
    latency_distribution: Dict[str, int] = field(default_factory=dict)
    latency_by_country: Dict[str, int] = field(default_factory=dict)
    latency_by_protocol: Dict[str, int] = field(default_factory=dict)
    smart_chains_breakdown: Dict[str, int] = field(default_factory=dict)

    @property
    def vwarp_win_rate(self) -> float:
        if self.vwarp_attempts == 0:
            return 0.0
        return (self.vwarp_success / self.vwarp_attempts) * 100

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Thread-safe method to get a snapshot of stats.
        """
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a dictionary representation of stats.
        Uses a threading.Lock for thread-safe access to dict fields.
        This is intentionally synchronous since it only uses threading.Lock.
        """
        with self._lock:
            # Sync duplicate fields
            self.total_lines_sourced = self.fetched_lines
            self.total_unique_candidates = self.parsed
            self.total_tested = self.tested
            self.total_working = self.working
            self.total_valid_proxies = self.working
            self.total_proxies = self.working + self.smart_chain_count
            self.total_revived = self.revived_warp + self.revived_vwarp
            self.total_clean = max(0, self.working - self.total_revived)
            self.total_smart_chains = self.smart_chain_count
            self.duration_seconds = self.duration
            if self.tested > 0:
                self.success_rate = self.working / self.tested

            return {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "total_configured_sources": self.total_configured_sources,
                "fetched_sources": self.fetched_sources,
                "fetched_lines": self.fetched_lines,
                "total_lines_sourced": self.total_lines_sourced,
                "parsed": self.parsed,
                "total_unique_candidates": self.total_unique_candidates,
                "tested": self.tested,
                "total_tested": self.total_tested,
                "working": self.working,
                "total_working": self.total_working,
                "total_valid_proxies": self.total_valid_proxies,
                "total_proxies": self.total_proxies,
                "total_clean": self.total_clean,
                "total_dirty": self.total_dirty,
                "geo_resolved": self.geo_resolved,
                "duration": self.duration,
                "duration_seconds": self.duration_seconds,
                "final_count": self.final_count,
                "cache_misses": self.cache_misses,
                "success_rate": self.success_rate,
                "scanner_ips_found": self.scanner_ips_found,
                "washer_success_count": self.washer_success_count,
                "smart_chain_count": self.smart_chain_count,
                "total_smart_chains": self.total_smart_chains,
                "chain_outbounds_count": self.chain_outbounds_count,
                "time_limited": self.time_limited,
                "time_limit_seconds": self.time_limit_seconds,
                "chosen_subset_size": self.chosen_subset_size,
                "revived_warp": self.revived_warp,
                "revived_vwarp": self.revived_vwarp,
                "shielded_count": self.shielded_count,
                "total_revived": self.total_revived,
                "warp_attempts": self.warp_attempts,
                "evasion_utls_enabled": self.evasion_utls_enabled,
                "evasion_alpn_enabled": self.evasion_alpn_enabled,
                "evasion_fragmentation_enabled": self.evasion_fragmentation_enabled,
                "evasion_multiplexing_enabled": self.evasion_multiplexing_enabled,
                "evasion_dns_safe_count": self.evasion_dns_safe_count,
                "evasion_dns_hardened_count": self.evasion_dns_hardened_count,
                "vwarp_attempts": self.vwarp_attempts,
                "vwarp_success": self.vwarp_success,
                "vwarp_win_rate": self.vwarp_win_rate,
                "washing_enabled": self.washing_enabled,
                # Create a shallow copy of the dict to prevent iteration errors
                "drop_reasons": dict(self.drop_reasons),
                "protocols": dict(self.protocols),
                "country_stats": dict(self.country_stats),
                "asns": dict(self.asns),
                "latency_distribution": dict(self.latency_distribution),
                "latency_by_country": dict(self.latency_by_country),
                "latency_by_protocol": dict(self.latency_by_protocol),
                "smart_chains_breakdown": dict(self.smart_chains_breakdown),
            }


class PipelineResult:
    """Container for the outcome of a full pipeline run."""

    def __init__(
        self,
        success: bool,
        stats: PipelineStats,
        output_files: dict,
        error: Optional[str] = None,
    ):
        self.success = success
        self.stats = stats
        self.output_files = output_files
        self.error = error
