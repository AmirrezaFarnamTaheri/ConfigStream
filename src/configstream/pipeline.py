"""
The Core Pipeline Orchestrator.
Integrates fetching, parsing, testing, and output generation into a
high-concurrency, memory-efficient streaming workflow.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set

from rich.progress import Progress, TaskID

from .models import Proxy
from .testers import SingBoxTester
from .test_cache import TestResultCache
from .scheduler import SmartRetestScheduler
from .concurrency_manager import ConcurrencyManager
from .adaptive_timeout import AdaptiveTimeout
from .geoip import GeoIPResolver
from .source_quality import SourceQualityTracker
from .anomaly import AnomalyDetector
from .security.blocklist import DEFAULT_BLOCKLIST
from .performance import PerformanceTracker
from .proxy_history import ProxyHistoryTracker
from .filtering import filter_unique_endpoints

from .pipeline_core.stats import PipelineStats
from .pipeline_core.models import PipelineResult
from .pipeline_stages import (
    source_producer,
    processing_consumer,
)
from .pipeline_core.sorter import sort_proxies_pareto
from .pipeline_core.output_handler import generate_pipeline_outputs
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

    # [FIX] Cap max_workers globally to protect local network stack
    if max_workers <= 0:
        from .adaptive_workers import calculate_optimal_workers

        max_workers = calculate_optimal_workers(0)

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

    # Initialize Blocklist - Await update to ensure security rules apply to first batch
    logger.info("Initializing security blocklists...")
    await DEFAULT_BLOCKLIST.update()

    # Initialize GeoIP (Shared Singleton)
    geoip = GeoIPResolver()

    # Initialize Event Stream
    event_stream = EventStream(output_path)

    stats = PipelineStats()

    # Work Queue – allow larger buffer between producer and consumer
    # Increased from 500 to 1000 for better buffering and reduced blocking
    work_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    # Results Collection
    final_proxies: List[Proxy] = []
    seen_keys: Set[tuple] = set()
    seen_lock = asyncio.Lock()

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
        max_workers=max_workers,
    )

    # Determine parallel consumers based on workers, but keep reasonable limits
    # to avoid overwhelming the system with too many heavy testing loops.
    # Optimized scaling: 2 consumers for low workers, up to 8 for high workers
    # to maximize throughput while keeping the event loop responsive.
    if max_workers >= 200:
        num_consumers = 8
    elif max_workers >= 100:
        num_consumers = 6
    elif max_workers >= 50:
        num_consumers = 4
    else:
        num_consumers = 2

    # [FIX] Start Concurrency Tuner globally if fallback to Python tester is likely
    if not tester.go_tester.available:
        logger.info(
            "Go tester unavailable - Starting global concurrency tuner for Python fallback"
        )
        concurrency.start_tuner()

    logger.info(f"Starting pipeline with {num_consumers} parallel consumers")

    # Run Producer and Consumers concurrently
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
            num_consumers=num_consumers,
        )
    )

    consumer_tasks = []
    for _ in range(num_consumers):
        t = asyncio.create_task(
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
                history,
                progress,
                task_process,
                max_proxies,
                max_latency,
                country_filter,
                leniency,
                seen_lock=seen_lock,
            )
        )
        consumer_tasks.append(t)

    try:
        try:
            await asyncio.gather(producer_task, *consumer_tasks)
        except Exception:
            # Cancel all tasks on failure to avoid leaks/hangs
            for t in consumer_tasks:
                t.cancel()
            producer_task.cancel()
            # Wait for cancellations to complete
            await asyncio.gather(*consumer_tasks, return_exceptions=True)
            try:
                await producer_task
            except asyncio.CancelledError:
                pass
            raise

        # 5. Final Cleanup & Output

        # Deduplicate Endpoints (IP:Port)
        optimized_proxies = filter_unique_endpoints(final_proxies)

        # Pareto Sort (in-place)
        sort_proxies_pareto(optimized_proxies, history)

        stats.final_count = len(optimized_proxies)

        # Generate Outputs
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        stats.duration = float(duration)

        generated_files = await generate_pipeline_outputs(
            optimized_proxies, output_path, stats, history
        )

        # Save History & Cache
        # history.save() # ProxyHistoryTracker doesn't have a save method exposed in top level, usually handled by storage close
        test_cache.save()
        if timeout_tracker:
            timeout_tracker.save()

        return PipelineResult(success=True, stats=stats, output_files=generated_files)
    finally:
        # [FIX] Stop tuner if running
        await concurrency.stop_tuner()

        # Shutdown tester (Go process)
        if tester:
            await tester.close()

        # Ensure event stream is always closed to flush handles/buffers
        try:
            await event_stream.aclose()
        except Exception:
            logger.exception("Failed to close EventStream cleanly")
