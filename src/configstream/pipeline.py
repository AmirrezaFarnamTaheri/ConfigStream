"""
The Core Pipeline Orchestrator.
Integrates fetching, parsing, testing, and output generation into a
high-concurrency, memory-efficient streaming workflow.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set

from rich.progress import Progress, TaskID

from .models import Proxy
from .adapters import get_adapter
from .testers import SingBoxTester
from .test_cache import TestResultCache
from .scheduler import SmartRetestScheduler
from .concurrency_manager import ConcurrencyManager
from .adaptive_workers import calculate_optimal_workers
from .adaptive_timeout import AdaptiveTimeout
from .geoip import GeoIPResolver
from .source_quality import SourceQualityTracker
from .anomaly import AnomalyDetector
from .security.blocklist import DEFAULT_BLOCKLIST
from .consolidation import select_top_configs
from . import output
from .output_generators import generate_base64_subscription
from .performance import PerformanceTracker
from .proxy_history import ProxyHistoryTracker
from .intelligence.washer import ProxyWasher
from .filtering import filter_unique_endpoints
from .serialize import serialize_proxy
from .intelligence.vectors import generate_vectors

from .pipeline_stages import (
    PipelineStats,
    PipelineResult,
    source_producer,
    processing_consumer,
)
from .event_stream import EventStream

logger = logging.getLogger(__name__)


async def run_full_pipeline(
    sources: List[str],
    output_dir: str,
    max_workers: int = 0,  # 0 = Auto
    max_proxies: Optional[int] = None,
    timeout: int = 10,
    country_filter: Optional[str] = None,
    max_latency: Optional[int] = None,
    leniency: bool = False,
    strict_security: bool = False,
    progress: Optional[Progress] = None,
    proxies: Optional[List[Proxy]] = None,  # Pre-supplied proxies
    dry_run: bool = False,
) -> PipelineResult:
    """
    Execute the streaming proxy aggregation pipeline.
    """
    start_time = datetime.now(timezone.utc)
    tracker = PerformanceTracker()

    # 1. Initialization & Setup
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if max_workers <= 0:
        max_workers = calculate_optimal_workers()

    # Initialize Intelligence Stack
    timeout_tracker = AdaptiveTimeout()
    concurrency = ConcurrencyManager(
        asyncio.get_running_loop(), initial_limit=max_workers
    )
    test_cache = TestResultCache()
    scheduler = SmartRetestScheduler(cache=test_cache)
    history = ProxyHistoryTracker()

    # Initialize Advanced Intelligence
    quality_tracker = SourceQualityTracker()
    anomaly_detector = AnomalyDetector()

    # Initialize Blocklist
    asyncio.create_task(DEFAULT_BLOCKLIST.update())

    # Initialize GeoIP (Shared Singleton)
    geoip = GeoIPResolver()

    # Initialize Event Stream
    event_stream = EventStream(output_path)

    stats = PipelineStats()

    # Work Queue
    work_queue: asyncio.Queue = asyncio.Queue(maxsize=50)

    # Results Collection
    final_proxies: List[Proxy] = []
    seen_keys: Set[tuple] = set()

    # --- Progress Bar Setup ---
    task_fetch: Optional[TaskID] = None
    task_process: Optional[TaskID] = None
    if progress:
        task_fetch = progress.add_task(
            "[cyan]Fetching sources...", total=len(sources) if sources else 1
        )
        task_process = progress.add_task("[green]Processing pipeline...", total=None)

    # 2. Execute Pipeline
    logger.info(f"Starting pipeline with {max_workers} initial workers")

    tester = SingBoxTester(
        timeout=float(timeout),
        cache=test_cache,
        strict_security=strict_security,
        dry_run=dry_run,
    )

    # Run Producer and Consumer concurrently
    producer_task = asyncio.create_task(
        source_producer(
            sources,
            work_queue,
            proxies,
            quality_tracker,
            anomaly_detector,
            event_stream,
            progress,
            task_fetch,
        )
    )
    consumer_task = asyncio.create_task(
        processing_consumer(
            work_queue,
            stats,
            seen_keys,
            final_proxies,
            tester,
            scheduler,
            test_cache,
            concurrency,
            geoip,
            tracker,
            event_stream,
            quality_tracker,
            progress,
            task_process,
            max_proxies,
            max_latency,
            country_filter,
            leniency,
        )
    )

    await asyncio.gather(producer_task, consumer_task)

    # 5. Final Cleanup & Output

    # Deduplicate Endpoints (IP:Port)
    optimized_proxies = filter_unique_endpoints(final_proxies)

    # Pareto Sort: Latency (50%), Reliability/Uptime (30%), Success (20%)
    # We leverage the history tracker to get reliability scores.

    def pareto_score(p: Proxy) -> float:
        # Lower score is better
        latency = p.latency if p.latency else 9999

        # Normalize latency: 0-1000ms -> 0-1. Clamp at 1 (1s+)
        norm_latency = min(latency / 1000.0, 1.0)

        # Reliability (Success Rate) from History
        # Note: get_reliability_score returns 0-1 (higher is better)
        # We invert it so lower is better (1 - score)
        reliability = history.get_reliability_score(p.id)

        # Stability (Jitter)
        # We use uptime_percentage from summary as 'stability' proxy if available
        summary = history.get_summary_stats(p.id)
        uptime = summary.get("uptime_percentage", 50.0) / 100.0

        # Weighted Score
        # Latency: 50%
        # Reliability (History Success): 30%
        # Stability (Uptime): 20%

        score = (
            (norm_latency * 0.5) + ((1.0 - reliability) * 0.3) + ((1.0 - uptime) * 0.2)
        )
        return float(score)

    optimized_proxies.sort(key=pareto_score)

    # Generate Outputs
    logger.info(f"Generating outputs for {len(optimized_proxies)} proxies...")

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    stats.duration = float(duration)
    stats.final_count = len(optimized_proxies)

    # --- Intelligence Phase: Washing & Chaining (Centralized) ---
    washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))
    washed_outbounds, washed_ids = washer.wash_batch(optimized_proxies)

    smart_chains = output.generate_smart_chains(optimized_proxies)

    generated_files = output.generate_categorized_outputs(
        optimized_proxies,
        output_path,
        washed_outbounds=washed_outbounds,
        washed_ids=washed_ids,
        smart_chains=smart_chains,
    )

    # NEW: Generate Metadata for Frontend
    output.save_metadata(stats.to_dict(), optimized_proxies, output_path)

    # NEW: Generate Static Vectors for Client-Side Search
    generate_vectors(optimized_proxies, output_path)

    # New Adapters Exports
    try:
        # Pass washed_outbounds to adapters that support it (Surge)
        (output_path / "surge.conf").write_text(
            get_adapter("surge").export(optimized_proxies, washed_outbounds)
        )
        (output_path / "shadowrocket.txt").write_text(
            get_adapter("shadowrocket").export(optimized_proxies, washed_outbounds)
        )
        # Loon
        (output_path / "loon.conf").write_text(
            get_adapter("loon").export(optimized_proxies, washed_outbounds)
        )
        # Quantumult X
        (output_path / "quantumult.conf").write_text(
            get_adapter("qx").export(optimized_proxies, washed_outbounds)
        )
        # SIP008
        (output_path / "sip008.json").write_text(
            get_adapter("sip008").export(optimized_proxies, washed_outbounds)
        )
    except Exception as e:
        logger.error(f"Failed to export adapters: {e}")

    # Chosen 1000 Generation
    chosen_proxies = select_top_configs(
        optimized_proxies, top_per_protocol=50, total_limit=1000
    )
    chosen_dir = output_path / "chosen"
    chosen_dir.mkdir(exist_ok=True)

    (chosen_dir / "proxies.json").write_text(
        json.dumps(
            [serialize_proxy(p, history.get_history(p.id)) for p in chosen_proxies],
            indent=2,
        )
    )
    (chosen_dir / "base64.txt").write_text(generate_base64_subscription(chosen_proxies))

    # Save History & Cache
    history.save()
    test_cache.save()
    if timeout_tracker:
        timeout_tracker.save()

    return PipelineResult(success=True, stats=stats, output_files=generated_files)
