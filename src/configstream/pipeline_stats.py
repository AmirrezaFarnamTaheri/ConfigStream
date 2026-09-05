# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import threading

__all__ = ["PipelineExecutionAudit", "PipelineStats", "PipelineResult"]


@dataclass
class PipelineExecutionAudit:
    """Execution-level audit summary for post-run diagnostics."""

    trace_id: str
    tested: int
    working: int
    total_revived: int
    revived_warp: int
    revived_vwarp: int
    revival_attempts: int
    revival_win_rate: float
    fetched_sources: int
    total_sources: int
    source_toxicity_rate: float
    backpressure_drop: int
    time_limited: bool
    hard_timeout: bool
    abandoned_queue_items: int
    abandoned_queue_lines: int

    @classmethod
    def from_stats(cls, stats: "PipelineStats") -> "PipelineExecutionAudit":
        attempts = int(stats.warp_attempts) + int(stats.vwarp_attempts)
        if attempts <= 0:
            attempts = int(stats.total_revived)
        revived = int(stats.total_revived)
        revival_win_rate = (revived / attempts) * 100.0 if attempts > 0 else 0.0

        toxic_drops = (
            int(stats.drop_reasons.get("fetch_error", 0))
            + int(stats.drop_reasons.get("security_validation", 0))
            + int(stats.drop_reasons.get("hostile_payload", 0))
        )
        denom = max(1, int(stats.fetched_sources))
        toxicity_rate = (toxic_drops / denom) * 100.0

        return cls(
            trace_id=stats.trace_id or "-",
            tested=int(stats.tested),
            working=int(stats.working),
            total_revived=revived,
            revived_warp=int(stats.revived_warp),
            revived_vwarp=int(stats.revived_vwarp),
            revival_attempts=attempts,
            revival_win_rate=revival_win_rate,
            fetched_sources=int(stats.fetched_sources),
            total_sources=int(stats.total_sources),
            source_toxicity_rate=toxicity_rate,
            backpressure_drop=int(stats.backpressure_drop),
            time_limited=bool(stats.time_limited),
            hard_timeout=bool(stats.hard_timeout),
            abandoned_queue_items=int(stats.abandoned_queue_items),
            abandoned_queue_lines=int(stats.abandoned_queue_lines),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "tested": self.tested,
            "working": self.working,
            "total_revived": self.total_revived,
            "revived_warp": self.revived_warp,
            "revived_vwarp": self.revived_vwarp,
            "revival_attempts": self.revival_attempts,
            "revival_win_rate": self.revival_win_rate,
            "fetched_sources": self.fetched_sources,
            "total_sources": self.total_sources,
            "source_toxicity_rate": self.source_toxicity_rate,
            "backpressure_drop": self.backpressure_drop,
            "time_limited": self.time_limited,
            "hard_timeout": self.hard_timeout,
            "abandoned_queue_items": self.abandoned_queue_items,
            "abandoned_queue_lines": self.abandoned_queue_lines,
        }


@dataclass
class PipelineStats:
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    trace_id: str = "-"
    drop_reasons: Dict[str, int] = field(default_factory=dict)

    # Internal lock for thread-safe access to dictionary fields
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # Canonical Stats
    total_configured_sources: int = (
        0  # Total sources from sources.yaml (for frontend display)
    )
    fetched_sources: int = 0  # Sources actually processed
    fetched_lines: int = 0  # Raw lines fetched
    parsed: int = 0  # Valid proxies parsed
    tested: int = 0  # Proxies sent to testing
    working: int = 0  # Proxies that passed testing
    geo_resolved: int = 0
    duration: float = 0.0
    final_count: int = 0
    cache_misses: int = 0

    # Intelligence Layer Stats
    scanner_ips_found: int = 0
    washer_success_count: int = 0
    smart_chain_count: int = 0
    chain_obs_count: int = 0
    backpressure_drop: int = 0
    # Time budget handling
    time_limited: bool = False
    time_limit_seconds: int = 0
    # ``time_limited`` means intake stopped at the configured window and the
    # queue was allowed to drain. ``hard_timeout`` means the grace window also
    # expired and work had to be cancelled; such a run is not publishable.
    hard_timeout: bool = False
    abandoned_queue_items: int = 0
    abandoned_queue_lines: int = 0

    # Revived Stats
    revived_warp: int = 0
    revived_vwarp: int = 0
    # Candidate chains created by shielding (Copper to Gold). These are not
    # counted as working unless they are retested and represented in `working`.
    shielded_count: int = 0
    shielded_candidate_count: int = 0
    shielded_verified_count: int = 0

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

    # Metadata mirror fields (frontend consumes these keys directly)
    protocols: Dict[str, int] = field(default_factory=dict)
    country_stats: Dict[str, int] = field(default_factory=dict)
    asns: Dict[str, int] = field(default_factory=dict)
    latency_distribution: Dict[str, int] = field(
        default_factory=lambda: {"fast": 0, "medium": 0, "slow": 0, "very_slow": 0}
    )
    latency_by_country: Dict[str, int] = field(default_factory=dict)
    latency_by_protocol: Dict[str, int] = field(default_factory=dict)
    smart_chains_breakdown: Dict[str, int] = field(default_factory=dict)
    total_dirty: int = 0
    chosen_subset_size: int = 0

    @property
    def vwarp_win_rate(self) -> float:
        if self.vwarp_attempts == 0:
            return 0.0
        return (self.vwarp_success / self.vwarp_attempts) * 100

    @property
    def success_rate(self) -> float:
        if self.tested == 0:
            return 0.0
        return self.working / self.tested

    @property
    def total_revived(self) -> int:
        return self.revived_warp + self.revived_vwarp

    @property
    def total_clean(self) -> int:
        return max(0, self.working - self.total_revived)

    @property
    def total_lines_sourced(self) -> int:
        return self.fetched_lines

    @property
    def total_unique_candidates(self) -> int:
        return self.parsed

    @property
    def total_valid_proxies(self) -> int:
        return self.working

    @property
    def total_proxies(self) -> int:
        return self.working + self.smart_chain_count

    @property
    def total_tested(self) -> int:
        return self.tested

    @property
    def total_working(self) -> int:
        return self.working

    @property
    def total_smart_chains(self) -> int:
        return self.smart_chain_count

    @property
    def rejection_reasons(self) -> Dict[str, int]:
        return dict(self.drop_reasons)

    @property
    def sources_count(self) -> int:
        return self.total_configured_sources

    @property
    def total_sources(self) -> int:
        return self.total_configured_sources

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Thread-safe method to get a snapshot of stats.
        """
        return self.to_dict()

    def add_drop_reason(self, reason: str, count: int = 1) -> None:
        """Thread-safe increment for drop reason counters."""
        if count <= 0:
            return
        with self._lock:
            self.drop_reasons[reason] = self.drop_reasons.get(reason, 0) + count

    def record_backpressure_drop(self, count: int = 1) -> None:
        """Thread-safe backpressure drop accounting."""
        if count <= 0:
            return
        with self._lock:
            self.backpressure_drop += count
            self.drop_reasons["backpressure_drop"] = (
                self.drop_reasons.get("backpressure_drop", 0) + count
            )

    def record_abandoned_work(self, line_count: int, item_count: int = 1) -> None:
        """Account work abandoned only during a forced hard-timeout teardown."""
        if line_count < 0 or item_count <= 0:
            return
        with self._lock:
            self.abandoned_queue_items += int(item_count)
            self.abandoned_queue_lines += int(line_count)
            if line_count:
                self.drop_reasons["hard_timeout_abandoned"] = (
                    self.drop_reasons.get("hard_timeout_abandoned", 0)
                    + int(line_count)
                )

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a dictionary representation of stats.
        Uses a threading.Lock for thread-safe access to dict fields.
        This is intentionally synchronous since it only uses threading.Lock.
        """
        with self._lock:
            return {
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "trace_id": self.trace_id or "-",
                "total_configured_sources": self.total_configured_sources,
                "fetched_sources": self.fetched_sources,
                "fetched_lines": self.fetched_lines,
                "parsed": self.parsed,
                "tested": self.tested,
                "working": self.working,
                "geo_resolved": self.geo_resolved,
                "duration": self.duration,
                "final_count": self.final_count,
                "cache_misses": self.cache_misses,
                "scanner_ips_found": self.scanner_ips_found,
                "washer_success_count": self.washer_success_count,
                "smart_chain_count": self.smart_chain_count,
                "chain_obs_count": self.chain_obs_count,
                "backpressure_drop": self.backpressure_drop,
                "time_limited": self.time_limited,
                "time_limit_seconds": self.time_limit_seconds,
                "hard_timeout": self.hard_timeout,
                "abandoned_queue_items": self.abandoned_queue_items,
                "abandoned_queue_lines": self.abandoned_queue_lines,
                "revived_warp": self.revived_warp,
                "revived_vwarp": self.revived_vwarp,
                "shielded_count": self.shielded_count,
                "shielded_candidate_count": self.shielded_candidate_count,
                "shielded_verified_count": self.shielded_verified_count,
                "total_revived": self.total_revived,
                "total_clean": self.total_clean,
                "total_dirty": self.total_dirty,
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
                "success_rate": self.success_rate,
                "total_lines_sourced": self.total_lines_sourced,
                "total_unique_candidates": self.total_unique_candidates,
                "total_valid_proxies": self.total_valid_proxies,
                "total_proxies": self.total_proxies,
                "total_tested": self.total_tested,
                "total_working": self.total_working,
                "total_smart_chains": self.total_smart_chains,
                "protocols": dict(self.protocols),
                "country_stats": dict(self.country_stats),
                "asns": dict(self.asns),
                "latency_distribution": dict(self.latency_distribution),
                "latency_by_country": dict(self.latency_by_country),
                "latency_by_protocol": dict(self.latency_by_protocol),
                "smart_chains_breakdown": dict(self.smart_chains_breakdown),
                "rejection_reasons": self.rejection_reasons,
                "sources_count": self.sources_count,
                "total_sources": self.total_sources,
                "chosen_subset_size": self.chosen_subset_size,
                "pipeline_execution_audit": PipelineExecutionAudit.from_stats(
                    self
                ).to_dict(),
                # Create a shallow copy of the dict to prevent iteration errors
                "drop_reasons": dict(self.drop_reasons),
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
