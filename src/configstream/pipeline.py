"""
The Core Pipeline Orchestrator.
Integrates fetching, parsing, testing, and output generation into a
high-concurrency, memory-efficient streaming workflow.
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import shutil
import subprocess
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
from .pipeline_core import output_handler
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
    # [FIX] Track total configured sources for frontend display
    stats.total_configured_sources = len(sources) if sources else 0

    # --- Start Vwarp Tunnel if available ---
    vwarp_proc = None
    vwarp_bin = shutil.which("vwarp") or "/usr/local/bin/vwarp"
    if os.path.exists(vwarp_bin):
        try:
            logger.info("🚀 Starting Vwarp SOCKS5 Tunnel on port 10808...")
            vwarp_proc = subprocess.Popen(
                [vwarp_bin, "--bind", "127.0.0.1:10808"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Give it a second to bind
            await asyncio.sleep(1)
            # Signal Go Tester to use it
            os.environ["USE_VWARP_TUNNEL"] = "true"
        except Exception as e:
            logger.warning(f"Failed to start Vwarp tunnel: {e}")

    # Dynamic Worker Calculation based on CPU
    cpu_count = multiprocessing.cpu_count()
    # Use 1.5x cores for I/O bound tasks, clamped between 4 and 32 for stability
    optimal_consumers = max(4, min(int(cpu_count * 1.5), 32))

    # Allow override if max_workers is very high, implying user wants aggressive parallelism
    if max_workers > 200:
        optimal_consumers = max(optimal_consumers, 16)

    logger.info(
        f"🚀 Auto-scaling to {optimal_consumers} consumers based on {cpu_count} cores."
    )

    # Optimized Queue Size: Increase buffer to prevent producer blocking
    work_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)

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

    # [FIX] Start Concurrency Tuner globally if fallback to Python tester is likely
    if not tester.go_tester.available:
        logger.info(
            "Go tester unavailable - Starting global concurrency tuner for Python fallback"
        )
        concurrency.start_tuner()

    logger.info(f"Starting pipeline with {optimal_consumers} parallel consumers")

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
            num_consumers=optimal_consumers,
        )
    )

    consumer_tasks = []
    for _ in range(optimal_consumers):
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

        generated_files = await output_handler.generate_pipeline_outputs(
            optimized_proxies, output_path, stats, history
        )

        # Save History & Cache
        # history.save() # ProxyHistoryTracker doesn't have a save method exposed in top level, usually handled by storage close
        test_cache.save()
        if timeout_tracker:
            timeout_tracker.save()

        # Trigger Server Update Notification
        # If API server is running on localhost, we notify it
        try:
            pass  # from .server import manager as ws_manager
            # Only if running in same process, which is rare for pipeline vs server split.
            # But we can try hitting the endpoint.
            import httpx

            async with httpx.AsyncClient(timeout=1.0) as client:
                await client.post(
                    "http://127.0.0.1:8000/api/admin/notify-update",
                    json={"timestamp": stats.end_time or duration},
                )
        except Exception:
            pass

        return PipelineResult(success=True, stats=stats, output_files=generated_files)
    finally:
        # [FIX] Stop tuner if running
        await concurrency.stop_tuner()

        # Shutdown tester (Go process)
        if tester:
            await tester.close()

        # Shutdown Vwarp tunnel
        if vwarp_proc:
            try:
                vwarp_proc.terminate()
                vwarp_proc.wait(timeout=2)
            except Exception:
                vwarp_proc.kill()

        # Ensure event stream is always closed to flush handles/buffers
        try:
            await event_stream.aclose()
        except Exception:
            logger.exception("Failed to close EventStream cleanly")
