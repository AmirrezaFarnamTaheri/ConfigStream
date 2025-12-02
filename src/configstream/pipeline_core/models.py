from dataclasses import dataclass
from typing import Dict, Union, Optional

@dataclass
class PipelineStats:
    fetched_sources: int = 0
    fetched_lines: int = 0
    parsed: int = 0
    tested: int = 0
    working: int = 0
    geo_resolved: int = 0
    duration: float = 0.0
    final_count: int = 0
    cache_misses: int = 0

    def to_dict(self) -> Dict[str, Union[int, float]]:
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
        }

class PipelineResult:
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
