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
from typing import List, Optional, Dict

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
from .filtering import filter_unique_endpoints
from .constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS

from configstream.pipeline_core.stats import PipelineStats
from configstream.pipeline_core.models import PipelineResult
from configstream.pipeline_stages import (
    source_producer,
    processing_consumer,
)
from configstream.pipeline_core.sorter import sort_proxies_pareto
from configstream.pipeline_core import output_handler
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

    Args:
        sources: List of source URLs to fetch proxies from
        output_dir: Output directory path for generated files
        max_workers: Maximum concurrent workers (0 = auto-calculate)
        max_proxies: Maximum number of proxies to process (None = unlimited)
        timeout: Proxy test timeout in seconds
        country_filter: ISO country code filter (e.g., "US", "GB")
        max_latency: Maximum acceptable latency in milliseconds
        leniency: Enable lenient testing mode
        strict_security: Enable strict security checks
        progress: Optional Rich progress bar instance
        proxies: Pre-supplied proxy list (bypasses source fetching)
        dry_run: Skip actual proxy testing (validation mode)

    Returns:
        PipelineResult with statistics and output file paths

    Raises:
        ValueError: If input parameters are invalid
        RuntimeError: If pipeline execution fails
    """
    # [FIX P2-6] Input validation - prevent invalid parameter combinations
    if not sources and not proxies:
        raise ValueError("Either 'sources' or 'proxies' must be provided")

    if not output_dir or not output_dir.strip():
        raise ValueError("'output_dir' must be a non-empty string")

    if max_workers < 0:
        raise ValueError(f"'max_workers' must be >= 0 (got {max_workers})")

    if max_workers > 10000:
        logger.warning(
            f"max_workers={max_workers} is extremely high - clamping to 1000 for stability"
        )
        max_workers = 1000

    if max_proxies is not None and max_proxies <= 0:
        raise ValueError(f"'max_proxies' must be > 0 or None (got {max_proxies})")

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
            logger.info(
                f"🚀 Starting Vwarp SOCKS5 Tunnel on port {VWARP_SOCKS5_PORT}..."
            )
            vwarp_proc = subprocess.Popen(
                [vwarp_bin, "--bind", f"{VWARP_BIND_ADDRESS}:{VWARP_SOCKS5_PORT}"],
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
    # Use Dict for ordered tracking (Python 3.7+ dicts preserve insertion order)
    seen_keys: Dict[tuple, None] = {}
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
        await concurrency.start_tuner()

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
        except (asyncio.CancelledError, KeyboardInterrupt, SystemExit) as e:
            # [FIX P2-1] Specific exception handling for graceful shutdown
            logger.info(f"Pipeline interrupted: {type(e).__name__}")
            # Cancel all tasks on interruption to avoid leaks/hangs
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
        except (RuntimeError, ValueError, TypeError) as e:
            # [FIX P2-1] Catch common pipeline errors with proper logging
            logger.error(f"Pipeline execution error: {e}")
            for t in consumer_tasks:
                t.cancel()
            producer_task.cancel()
            await asyncio.gather(*consumer_tasks, return_exceptions=True)
            try:
                await producer_task
            except asyncio.CancelledError:
                pass
            raise
        except Exception as e:
            # [FIX P2-1] Unexpected errors - log with full context
            logger.exception(f"Unexpected pipeline error: {e}")
            for t in consumer_tasks:
                t.cancel()
            producer_task.cancel()
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
        # [FIX] Set end_time for proper tracking
        stats.end_time = datetime.now(timezone.utc)
        duration = (stats.end_time - start_time).total_seconds()
        stats.duration = float(duration)

        generated_files = await output_handler.generate_pipeline_outputs(
            optimized_proxies, output_path, stats, history
        )

        # Save History & Cache
        history.save()  # [FIX] Persist history data - method exists at proxy_history.py:75-77
        test_cache.save()
        if timeout_tracker:
            timeout_tracker.save()

        # Trigger Server Update Notification
        # If API server is running on localhost, we notify it
        try:
            # from .server import manager as ws_manager
            # Only if running in same process, which is rare for pipeline vs server split.
            # But we can try hitting the endpoint.
            import httpx

            async with httpx.AsyncClient(timeout=1.0) as client:
                await client.post(
                    "http://127.0.0.1:8000/api/admin/notify-update",
                    json={"timestamp": stats.end_time or duration},
                )
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # [FIX P2-1] Server not running or unreachable - expected in standalone mode
            logger.debug(f"Server notification skipped (server not available): {e}")
        except httpx.HTTPStatusError as e:
            # [FIX P2-1] Server returned error status
            logger.warning(
                f"Server notification failed with HTTP {e.response.status_code}"
            )
        except Exception as e:
            # [FIX P2-1] Unexpected notification error
            logger.debug(f"Unexpected error during server notification: {e}")

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
            except subprocess.TimeoutExpired:
                # [FIX P2-1] Process didn't terminate gracefully - force kill
                logger.warning(
                    "Vwarp process didn't terminate gracefully, forcing kill"
                )
                vwarp_proc.kill()
                try:
                    vwarp_proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    logger.error("Failed to kill Vwarp process")
            except ProcessLookupError:
                # [FIX P2-1] Process already terminated
                logger.debug("Vwarp process already terminated")
            except Exception as e:
                # [FIX P2-1] Unexpected error during Vwarp cleanup
                logger.warning(f"Unexpected error during Vwarp cleanup: {e}")
                try:
                    vwarp_proc.kill()
                except Exception:
                    pass

        # Ensure event stream is always closed to flush handles/buffers
        try:
            await event_stream.aclose()
        except (OSError, IOError) as e:
            # [FIX P2-1] File handle errors during stream closure
            logger.error(f"I/O error closing EventStream: {e}")
        except RuntimeError as e:
            # [FIX P2-1] Runtime errors (e.g., event loop closed)
            logger.warning(f"Runtime error closing EventStream: {e}")
        except Exception as e:
            # [FIX P2-1] Unexpected errors - log with full traceback
            logger.exception(f"Unexpected error closing EventStream: {e}")
