# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import threading


@dataclass
class PipelineStats:
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
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
    # Time budget handling
    time_limited: bool = False
    time_limit_seconds: int = 0

    # Revived Stats
    revived_warp: int = 0
    revived_vwarp: int = 0

    # Vwarp Stats (Efficiency of Vwarp Tool specifically)
    warp_attempts: int = 0  # Standard WARP attempts
    vwarp_attempts: int = 0
    vwarp_success: int = 0

    # Washing Enabled Flag
    washing_enabled: bool = True

    @property
    def vwarp_win_rate(self) -> float:
        if self.vwarp_attempts == 0:
            return 0.0
        return (self.vwarp_success / self.vwarp_attempts) * 100

    @property
    def total_revived(self) -> int:
        return self.revived_warp + self.revived_vwarp

    async def get_snapshot(self) -> Dict[str, Any]:
        """
        Thread-safe method to get a snapshot of stats.
        """
        return await self.to_dict()

    async def to_dict(self) -> Dict[str, Any]:
        """
        Return a dictionary representation of stats.
        Uses defensive copies for complex types.
        """
        with self._lock:
            return {
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
                "time_limited": self.time_limited,
                "time_limit_seconds": self.time_limit_seconds,
                "revived_warp": self.revived_warp,
                "revived_vwarp": self.revived_vwarp,
                "total_revived": self.total_revived,
                "warp_attempts": self.warp_attempts,
                "vwarp_attempts": self.vwarp_attempts,
                "vwarp_success": self.vwarp_success,
                "vwarp_win_rate": self.vwarp_win_rate,
                "washing_enabled": self.washing_enabled,
                # Create a shallow copy of the dict to prevent iteration errors
                "drop_reasons": dict(self.drop_reasons),
            }
