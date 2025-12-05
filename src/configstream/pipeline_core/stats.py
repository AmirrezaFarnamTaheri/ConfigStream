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

    # New Stats for Intelligence Layer
    scanner_ips_found: int = 0
    washer_success_count: int = 0
    smart_chain_count: int = 0
