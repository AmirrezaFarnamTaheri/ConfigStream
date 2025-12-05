from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime, timezone


@dataclass
class PipelineStats:
    total_sourced: int = 0
    total_proxies: int = 0  # To be deprecated or merged with total_sourced?
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    drop_reasons: Dict[str, int] = field(default_factory=dict)

    # Compatible Fields for Models
    fetched_sources: int = 0
    fetched_lines: int = 0
    parsed: int = 0
    tested: int = 0
    working: int = 0
    geo_resolved: int = 0
    duration: float = 0.0
    final_count: int = 0
    cache_misses: int = 0

    # New Stats for Intelligence Layer
    scanner_ips_found: int = 0
    washer_success_count: int = 0
    smart_chain_count: int = 0

    def to_dict(self) -> Dict[str, int | float]:
        return {
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
        }
