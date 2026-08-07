# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Tuple
import asyncio
from configstream.models import Proxy
from configstream.pipeline_stats import PipelineStats

# Domain dependencies
from configstream.testers import SingBoxTester
from configstream.test_cache import TestResultCache
from configstream.scheduler import SmartRetestScheduler
from configstream.concurrency_manager import ConcurrencyManager
from configstream.source_quality import SourceQualityTracker
from configstream.anomaly import AnomalyDetector
from configstream.performance import PerformanceTracker
from configstream.history.tracker import ProxyHistoryTracker
from configstream.event_stream import EventStream
from configstream.intelligence.washer.core import ProxyWasher
from configstream.utils.bloom import BloomFilter
from configstream.hard_stop import HardStopWatcher
from configstream.config import AppSettings

if TYPE_CHECKING:
    from configstream.geoip import GeoData


class GeoIPLookup(Protocol):
    async def lookup(self, ip: str) -> Optional["GeoData"]: ...


@dataclass
class WorkItem:
    source: str
    lines: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    work_queue: asyncio.Queue[WorkItem]
    stop_event: asyncio.Event
    stats: PipelineStats
    final_proxies: List[Proxy]
    seen_keys: Dict[Tuple[Any, ...], None]
    seen_lock: asyncio.Lock
    settings: AppSettings

    # Trackers & Singletons
    tester: Optional[SingBoxTester] = None
    scheduler: Optional[SmartRetestScheduler] = None
    test_cache: Optional[TestResultCache] = None
    concurrency: Optional[ConcurrencyManager] = None
    geoip: Optional[GeoIPLookup] = None
    tracker: Optional[PerformanceTracker] = None
    event_stream: Optional[EventStream] = None
    quality_tracker: Optional[SourceQualityTracker] = None
    history: Optional[ProxyHistoryTracker] = None
    anomaly_detector: Optional[AnomalyDetector] = None
    washer: Optional[ProxyWasher] = None
    seen_bloom: Optional[BloomFilter] = None
    hard_stop_watcher: Optional[HardStopWatcher] = None
    # The VwarpTool instance that actually started the tunnel, if any. Must be
    # the same instance so shutdown can terminate the child it spawned.
    vwarp_tool: Optional[Any] = None

    # UI / Flow control
    progress: Optional[Any] = None
    task_process: Optional[Any] = None
    task_fetch: Optional[Any] = None

    # Filter config
    max_latency: Optional[int] = None
    country_filter: Optional[str] = None
    leniency: bool = False
    strict_security: bool = False
    dry_run: bool = False
    num_consumers: int = 4
