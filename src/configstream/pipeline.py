# SPDX-License-Identifier: AGPL-3.0-or-later
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
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict
from contextlib import suppress

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
from .history.tracker import ProxyHistoryTracker
from .filtering import dedupe_and_shuffle, filter_unique_endpoints, dedupe_by_config
from .constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS
from .utils.bloom import BloomFilter
from .async_utils import safe_wait_for
from .hard_stop import HardStopWatcher
from .logging_config import set_trace_id, clear_trace_id

from configstream.pipeline_stats import PipelineStats, PipelineResult
from configstream.producer import source_producer
from configstream.consumer import processing_consumer
from configstream.sorter import sort_proxies_pareto
import configstream.output_handler as output_handler
from .event_stream import EventStream
from configstream.intelligence.washer.core import ProxyWasher  # Import here
from .config import AppSettings
from configstream.security_validator import SecurityValidator

logger = logging.getLogger(__name__)


async def _cancel_all(
    producer_task: asyncio.Task, consumer_tasks: List[asyncio.Task]
) -> None:
    """Cancel producer and all consumer tasks, waiting for them to finish."""
    for t in consumer_tasks:
        t.cancel()
    producer_task.cancel()
    await asyncio.gather(*consumer_tasks, return_exceptions=True)
    with suppress(asyncio.CancelledError):
        await producer_task


async def run_full_pipeline(
    sources: List[str],
    output_dir: str,
    max_workers: int = 0,  # 0 = Auto
    timeout: int = 10,
    country_filter: Optional[str] = None,
    max_latency: Optional[int] = None,
    leniency: bool = False,
    strict_security: bool = False,
    progress: Optional[Progress] = None,
    proxies: Optional[List[Proxy]] = None,  # Pre-supplied proxies
    dry_run: bool = False,
    time_limit_seconds: Optional[int] = None,
) -> PipelineResult:
    """
    Execute the streaming proxy aggregation pipeline.

    Args:
        sources: List of source URLs to fetch proxies from
        output_dir: Output directory path for generated files
        max_workers: Maximum concurrent workers (0 = auto-calculate)
        timeout: Proxy test timeout in seconds
        country_filter: ISO country code filter (e.g., "US", "GB")
        max_latency: Maximum acceptable latency in milliseconds
        leniency: Enable lenient testing mode
        strict_security: Enable strict security checks
        progress: Optional Rich progress bar instance
        proxies: Pre-supplied proxy list (bypasses source fetching)
        dry_run: Skip actual proxy testing (validation mode)
        time_limit_seconds: Optional soft time limit for the batch (0 disables)

    Returns:
        PipelineResult with statistics and output file paths

    Raises:
        ValueError: If input parameters are invalid
        RuntimeError: If pipeline execution fails
    """
    # Input validation - prevent invalid parameter combinations
    if not sources and not proxies:
        raise ValueError("Either 'sources' or 'proxies' must be provided")

    if not output_dir or not output_dir.strip():
        raise ValueError("'output_dir' must be a non-empty string")

    if max_workers < 0:
        raise ValueError(f"'max_workers' must be >= 0 (got {max_workers})")

    settings = AppSettings()
    if max_workers <= 0 and settings.MAX_WORKERS > 0:
        max_workers = settings.MAX_WORKERS

    if not strict_security and settings.STRICT_SECURITY:
        strict_security = True

    if timeout <= 0 or timeout > 300:
        raise ValueError(f"'timeout' must be between 1 and 300 seconds (got {timeout})")

    if max_latency is not None and max_latency <= 0:
        raise ValueError(f"'max_latency' must be > 0 or None (got {max_latency})")

    if country_filter:
        # Validate ISO country code format (2 letters, uppercase)
        if not country_filter.isalpha() or len(country_filter) != 2:
            raise ValueError(
                f"'country_filter' must be a 2-letter ISO code (got '{country_filter}')"
            )
        country_filter = country_filter.upper()

    if time_limit_seconds is None:
        time_limit_seconds = settings.BATCH_TIME_LIMIT_SECONDS
    if time_limit_seconds is not None and time_limit_seconds < 0:
        raise ValueError(
            f"'time_limit_seconds' must be >= 0 (got {time_limit_seconds})"
        )

    start_time = datetime.now(timezone.utc)
    tracker = PerformanceTracker()
    trace_id = set_trace_id()

    # 1. Initialization & Setup
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Auto-calc max_workers if not explicitly provided
    if max_workers <= 0:
        from .adaptive_workers import calculate_optimal_workers

        max_workers = calculate_optimal_workers(0)

    # Initialize Intelligence Stack
    timeout_tracker = AdaptiveTimeout()
    concurrency = ConcurrencyManager(
        asyncio.get_running_loop(),
        initial_limit=max_workers,
        min_limit=1,
        max_limit=max_workers,
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

    # Initialize Shared Washer Singleton
    washer = ProxyWasher(settings.WARP_KEY_POOL)
    if not dry_run:
        await washer.fetch_clean_ips()  # Pre-fetch once

    # Initialize Event Stream
    event_stream = EventStream(output_path)

    stats = PipelineStats()
    stats.trace_id = trace_id
    # Track total configured sources for frontend display
    stats.total_configured_sources = len(sources) if sources else 0
    if time_limit_seconds:
        stats.time_limit_seconds = int(time_limit_seconds)
    hard_stop_watcher = HardStopWatcher(
        grace_seconds=float(getattr(settings, "SHUTDOWN_GRACE_SECONDS", 5.0)),
        flush_timeout_seconds=float(
            getattr(settings, "EVENT_STREAM_FLUSH_TIMEOUT_SECONDS", 2.0)
        ),
    )

    stop_event = asyncio.Event()
    test_budget: Optional[asyncio.Semaphore] = None

    # Validate App Settings
    settings.validate_settings()

    # --- Start Vwarp Tunnel if available ---
    # Use VwarpTool implementation to respect CI rules and improved logging
    from configstream.tools.vwarp import VwarpTool

    vwarp_tool = VwarpTool()
    # Tunnel lifecycle managed entirely by vwarp_tool.start_tunnel/stop_tunnel

    if settings.USE_VWARP_TUNNEL:
        if await vwarp_tool.is_available():
            vwarp_config_override = {
                "masque": {"enabled": settings.VWARP_MASQUE_ENABLED},
                "psiphon": {
                    "enabled": settings.PSIPHON_ENABLED,
                    "country": settings.PSIPHON_COUNTRY,
                },
            }
            if await vwarp_tool.start_tunnel(
                bind_addr=VWARP_BIND_ADDRESS,
                port=VWARP_SOCKS5_PORT,
                config_override=vwarp_config_override,
            ):
                logger.info("✅ Vwarp Tunnel established.")
                os.environ["USE_VWARP_TUNNEL"] = "true"
            else:
                logger.warning(
                    "Vwarp tunnel failed to start or did not pass health check. Disabling Vwarp integration."
                )
                os.environ["USE_VWARP_TUNNEL"] = "false"
        else:
            logger.warning(
                "Vwarp tunnel requested but vwarp binary is unavailable. Disabling Vwarp integration."
            )
            os.environ["USE_VWARP_TUNNEL"] = "false"
    else:
        logger.info("Vwarp tunnel disabled by configuration.")

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
    # Use Dict for ordered tracking (Python 3.7+ dicts preserve insertion order)
    seen_keys: Dict[tuple, None] = {}
    seen_bloom = None
    if settings.SEEN_BLOOM_ENABLED:
        seen_bloom = BloomFilter(
            expected_items=int(settings.SEEN_BLOOM_EXPECTED_ITEMS),
            false_positive_rate=float(settings.SEEN_BLOOM_FALSE_POSITIVE_RATE),
        )
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
    logger.info(
        "Starting pipeline with %d initial workers (trace_id=%s)",
        max_workers,
        trace_id,
    )

    tester = SingBoxTester(
        timeout=float(timeout),
        cache=test_cache,
        strict_security=strict_security,
        dry_run=dry_run,
        max_workers=max_workers,
    )

    # Log tester status once globally instead of per-consumer
    if tester.go_tester.available:
        logger.info("Using Go batch tester for proxy testing")
    else:
        logger.warning(
            "Go tester unavailable - Falling back to Python tester. "
            "Starting global concurrency tuner."
        )
        await concurrency.start_tuner()

    # Explicitly start Go tester to enable heartbeat/self-test
    if tester.go_tester.available:
        try:
            await tester.go_tester.start()
        except Exception as e:
            logger.warning(f"Failed to start Go tester daemon: {e}. Fallback enabled.")
            tester.go_tester.available = False

    logger.info(f"Starting pipeline with {optimal_consumers} parallel consumers")

    # Run Producer and Consumers concurrently
    time_limit_task: Optional[asyncio.Task] = None
    if time_limit_seconds and time_limit_seconds > 0:
        logger.info(
            f"Batch time limit enabled: {time_limit_seconds}s (soft stop with partial output)."
        )

        async def _time_limit_watcher() -> None:
            await asyncio.sleep(time_limit_seconds)
            if not stop_event.is_set():
                stats.time_limited = True
                stop_event.set()
                logger.warning(
                    "Batch time limit reached. Stopping intake and finalizing partial output."
                )

        time_limit_task = asyncio.create_task(_time_limit_watcher())
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
            stop_event=stop_event,
            stats=stats,
        )
    )

    consumer_tasks = []
    for i in range(optimal_consumers):
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
                max_latency,
                country_filter,
                leniency,
                consumer_id=i,
                seen_lock=seen_lock,
                washer=washer,  # Pass shared washer
                stop_event=stop_event,
                test_budget=test_budget,
                seen_bloom=seen_bloom,
            )
        )
        consumer_tasks.append(t)

    try:
        try:
            gather_task = asyncio.gather(producer_task, *consumer_tasks)
            if time_limit_seconds and time_limit_seconds > 0:
                grace_seconds = int(
                    getattr(settings, "BATCH_TIME_LIMIT_GRACE_SECONDS", 0)
                )
                hard_timeout = time_limit_seconds + max(0, grace_seconds)
                await safe_wait_for(gather_task, timeout=hard_timeout)
            else:
                await gather_task
        except asyncio.TimeoutError:
            # Hard stop to prevent CI timeouts when soft stop can't drain in time.
            stats.time_limited = True
            stop_event.set()
            logger.warning(
                "Hard batch time limit reached. Cancelling pipeline tasks to finalize output."
            )
            await _cancel_all(producer_task, consumer_tasks)
        except (asyncio.CancelledError, KeyboardInterrupt, SystemExit) as e:
            logger.info(f"Pipeline interrupted: {type(e).__name__}")
            await _cancel_all(producer_task, consumer_tasks)
            raise
        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            await _cancel_all(producer_task, consumer_tasks)
            raise

        # 5. Final Cleanup & Output

        # Log warning on 0 working proxies but ALWAYS proceed to output generation.
        # Proxies that failed testing in THIS environment may work for end-users in
        # different networks/regions.  Skipping output generation deprives them of
        # subscription files, DNS-safe variants, categorized outputs, and chain configs.
        # The is_working flag is preserved in the data so clients can filter if desired.
        _zero_working = stats.tested > 0 and stats.working == 0
        if _zero_working:
            logger.warning(
                f"All {stats.tested} proxy tests failed across all sources. "
                "Output will still be generated with is_working=False so downstream "
                "consumers can attempt their own connectivity checks."
            )

        # Deduplicate configs first, then drop duplicate tags/remarks, then endpoints (IP:Port).
        optimized_proxies = dedupe_and_shuffle(final_proxies)
        optimized_proxies = dedupe_by_config(optimized_proxies)
        if settings.ENABLE_ENDPOINT_FILTERING:
            optimized_proxies = filter_unique_endpoints(optimized_proxies)
        else:
            logger.info("Endpoint filtering disabled by configuration.")

        # Pareto Sort (in-place)
        sort_proxies_pareto(optimized_proxies, history)

        stats.final_count = len(optimized_proxies)

        # Generate Outputs
        # Set end_time for proper tracking
        stats.end_time = datetime.now(timezone.utc)
        duration = (stats.end_time - start_time).total_seconds()
        stats.duration = float(duration)

        # [FEATURE] Log Top 5 Failing Sources
        if quality_tracker:
            failing_sources = quality_tracker.get_worst_sources(limit=5)
            if failing_sources:
                log_lines = []
                for s_data in failing_sources:
                    safe_url = SecurityValidator.sanitize_log_message(s_data["url"])
                    log_lines.append(
                        f"  - {safe_url}: score={s_data['score']:.1f}, reason={s_data.get('last_failure_reason', 'unknown')}"
                    )
                logger.info("⚠️ Top 5 Failing Sources:\n" + "\n".join(log_lines))

        # Pass washer instance to reuse clean IPs and keys
        generated_files = await output_handler.generate_pipeline_outputs(
            optimized_proxies, output_path, stats, history, washer=washer
        )

        # Log scheduling and anomaly statistics for observability
        sched_stats = scheduler.get_scheduling_statistics()
        if sched_stats:
            logger.info(f"Scheduler stats: {sched_stats}")
        if anomaly_detector:
            anomaly_detector.get_statistics()

        # Save History & Cache
        history.save()  # Persist history data - method exists at proxy_history.py:75-77

        # Cleanup old history to prevent database bloat
        try:
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: history.cleanup_old_data(days=30)
            )
        except Exception as e:
            logger.warning(f"History cleanup failed: {e}")

        test_cache.save()
        if timeout_tracker:
            timeout_tracker.save()

        # Trigger Server Update Notification
        # If API server is running on localhost, we notify it
        try:
            import httpx

            async with httpx.AsyncClient(timeout=1.0) as client:
                await client.post(
                    "http://127.0.0.1:8000/api/admin/notify-update",
                    json={
                        "timestamp": (
                            stats.end_time.isoformat() if stats.end_time else duration
                        )
                    },
                )
        except Exception as e:
            logger.debug(f"Server notification skipped: {e}")

        should_fail = (strict_security or bool(getattr(settings, "FAIL_ON_ZERO_WORKING", False))) and bool(
            _zero_working
        )
        if should_fail:
            logger.error(
                "0 working proxies detected and strict mode is enabled; "
                "marking pipeline result as failed."
            )

        return PipelineResult(
            success=not should_fail,
            stats=stats,
            output_files=generated_files,
            error="0 working proxies detected" if should_fail else None,
        )
    finally:
        # Stop tuner if running
        await concurrency.stop_tuner()
        if time_limit_task:
            time_limit_task.cancel()
            with suppress(asyncio.CancelledError):
                await time_limit_task

        # Shutdown tester/processes with bounded grace and hard-stop fallback.
        await hard_stop_watcher.stop_tester(tester)

        # Shutdown Vwarp tunnel
        await vwarp_tool.stop_tunnel()

        # Close anomaly detector DB connection
        anomaly_detector.close()

        # Ensure event stream is always flushed/closed before process exit.
        await hard_stop_watcher.flush_event_stream(event_stream)
        clear_trace_id()
