"""
The Core Pipeline Orchestrator.
Integrates fetching, parsing, testing, and output generation into a
high-concurrency, memory-efficient streaming workflow.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Set, Dict, Union
from dataclasses import dataclass, field

from rich.progress import Progress, TaskID

# --- Core Modules ---
from .models import Proxy
from .config import AppSettings
from .auto_detect import auto_detect_and_parse as parse_config
from .parsers import _extract_config_lines
from .adapters import get_adapter

# --- Phase 1: Ingestion ---
from .fetcher import fetch_multiple_sources
from .async_file_ops import read_multiple_files_async

# --- Phase 2: Validation ---
from .security_validator import validate_batch_configs, STRICT_POLICY, TEST_POLICY
from .filtering import filter_unique_endpoints, proxy_unique_key

# --- Phase 3: Testing ---
from .testers import SingBoxTester
from .test_cache import TestResultCache

# --- Phase 4: Intelligence ---
from .scheduler import SmartRetestScheduler
from .concurrency_manager import ConcurrencyManager
from .adaptive_workers import calculate_optimal_workers
from .adaptive_timeout import AdaptiveTimeout
from .geoip import GeoIPResolver
from .source_quality import SourceQualityTracker, calculate_diversity_score
from .anomaly import AnomalyDetector
from .security.blocklist import DEFAULT_BLOCKLIST
from .event_stream import EventStream
from .consolidation import select_top_configs

# --- Output ---
from . import output
from .performance import PerformanceTracker
from .proxy_history import ProxyHistoryTracker

logger = logging.getLogger(__name__)


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
        self, success: bool, stats: PipelineStats, output_files: dict, error: str | None = None
    ):
        self.success = success
        self.stats = stats
        self.output_files = output_files
        self.error = error


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
    settings = AppSettings()
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

    # Initialize Event Stream
    event_stream = EventStream(output_path)
    event_stream.emit(
        "pipeline_start", f"Pipeline started with {len(sources)} sources."
    )

    # Initialize Blocklist
    asyncio.create_task(DEFAULT_BLOCKLIST.update())

    # Initialize GeoIP (Shared Singleton)
    geoip = GeoIPResolver()

    stats = PipelineStats()

    # Work Queue: Stores (source_url, raw_content_chunk)
    # We use a bounded queue to apply backpressure on the fetcher if processing is slow
    work_queue: asyncio.Queue[Tuple[str, List[str]] | None] = asyncio.Queue(maxsize=50)

    # Results Collection (Thread-safe via simple append in main loop, but here we gather)
    # We'll store working proxies in a list. For 100k+ proxies, this is fine in memory (approx 20-50MB).
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

    # 2. The Producer: Source Fetcher
    async def _source_producer():
        try:
            # A. Handle Pre-supplied Proxies (e.g. from previous run retest)
            if proxies:
                # Mock a source for these
                lines = [p.config for p in proxies if p.config]
                if lines:
                    await work_queue.put(("supplied-proxies", lines))

            # B. Handle File Sources
            local_files = [s for s in sources if not s.startswith("http")]
            if local_files:
                # We can read these efficiently in parallel
                file_results = await read_multiple_files_async(local_files)
                for fpath, content in file_results:
                    lines = _extract_config_lines(content)
                    if lines:
                        await work_queue.put((fpath, lines))
                    if progress and task_fetch:
                        progress.advance(task_fetch)

            # C. Handle Remote Sources
            remote_urls = []
            for s in sources:
                if s.startswith("http"):
                    remote_urls.append(s)
                # Handle individual proxy configs or non-standard schemes
                elif s.startswith(
                    (
                        "ss://",
                        "vmess://",
                        "vless://",
                        "trojan://",
                        "hysteria://",
                        "hy2://",
                        "tuic://",
                        "ssh://",
                        "wg://",
                        "wireguard://",
                    )
                ):
                    # Treat as a single-line config supplied directly
                    await work_queue.put(("supplied-config", [s]))
                elif s.startswith("ssconf://"):
                    # Convert ssconf to https for fetching
                    remote_urls.append(s.replace("ssconf://", "https://"))

            # NEW: Filter sources based on Quality/Cooldown
            active_urls = []
            for url in remote_urls:
                if quality_tracker.should_fetch(url):
                    active_urls.append(url)
                else:
                    # Log skipped source for stats
                    pass

            if active_urls:
                batch_size = 50
                for i in range(0, len(active_urls), batch_size):
                    batch = active_urls[i : i + batch_size]

                    results = await fetch_multiple_sources(
                        batch,
                        max_concurrent=settings.PER_HOST_MAX_CONCURRENCY,
                        timeout=settings.FETCH_TIMEOUT,
                        use_adaptive_timeout=True,
                    )

                    for source, res in results.items():
                        if res.success and res.content:
                            lines = _extract_config_lines(res.content)
                            count = len(lines)

                            # NEW: Anomaly Check
                            is_safe, reason = anomaly_detector.is_safe(source, count)

                            if is_safe:
                                if lines:
                                    # Record the "Fetch" event. We update "Working" later.
                                    anomaly_detector.record(source, count)
                                    event_stream.emit(
                                        "fetch_success",
                                        f"Fetched {count} proxies from {source}",
                                    )
                                    # Note: We pass the source URL along with the lines now
                                    # so the consumer knows where they came from
                                    await work_queue.put((source, lines))
                            else:
                                logger.warning(f"⚠️ BLOCKING {source}: {reason}")
                                event_stream.emit(
                                    "fetch_blocked",
                                    f"Blocked source {source}: {reason}",
                                )

                        # Note: If fetch failed, fetcher logs it.
                        # Quality tracker will penalize implicitly if we don't report success later.

        except Exception as e:
            logger.error("Producer failed: %s", e)
        finally:
            # Sentinel: Signal consumer to stop
            await work_queue.put(None)

    # 3. The Consumer: Parser & Tester
    async def _processing_consumer():
        tester = SingBoxTester(
            timeout=float(timeout),
            cache=test_cache,
            strict_security=strict_security,
            dry_run=dry_run,
        )

        policy = TEST_POLICY if leniency else STRICT_POLICY

        while True:
            item = await work_queue.get()
            if item is None:
                # Propagate sentinel if we had multiple consumers (we have 1 logic stream here)
                work_queue.task_done()
                break

            source, raw_lines = item
            stats.fetched_sources += 1
            stats.fetched_lines += len(raw_lines)

            # --- Parsing ---
            # Batch parse is faster
            # Run parsing in executor to prevent blocking the event loop
            # especially for large batches of regex/base64 operations
            loop = asyncio.get_running_loop()

            def _parse_chunk(lines, src):
                result = []
                for line in lines:
                    p = parse_config(line)
                    if p:
                        p.details["_source"] = src
                        result.append(p)
                return result

            parsed_batch = []
            with tracker.phase("parse"):
                parsed_batch = await loop.run_in_executor(
                    None, _parse_chunk, raw_lines, source
                )

            if not parsed_batch:
                work_queue.task_done()
                continue

            # --- Deduplication (Early) ---
            # Check against global seen set to avoid testing duplicates
            unique_batch = []
            for p in parsed_batch:
                k = proxy_unique_key(p)
                if k not in seen_keys:
                    seen_keys.add(k)
                    unique_batch.append(p)

            stats.parsed += len(unique_batch)

            # --- Security Validation ---
            safe_batch = validate_batch_configs(unique_batch, policy)

            # --- Smart Scheduling ---
            # Only test if necessary
            # to_test = scheduler.filter_proxies_for_retest(safe_batch)
            # We don't use to_test directly, we iterate safe_batch below

            # If we skipped some, we should pull them from cache to include in output
            # (The scheduler returns ONLY what needs testing, we need to merge back the valid cached ones)
            # Actually, for simplicity and correctness, if it's in cache and valid, we want it.
            # The scheduler logic was slightly simpler. Let's refine:

            final_batch_for_this_source = []

            # Separation:
            # 1. Needs Test -> Test -> Result
            # 2. Cached & Valid -> Use Cache

            proxies_to_actually_test = []
            for p in safe_batch:
                if scheduler.should_retest(p):
                    proxies_to_actually_test.append(p)
                else:
                    # It's healthy in cache
                    cached = test_cache.get(p)
                    if cached:
                        final_batch_for_this_source.append(cached)
                    else:
                        # Cache miss - retest instead of dropping proxy
                        logger.debug(f"Cache miss for {p.id}, will retest")
                        stats.cache_misses += 1
                        proxies_to_actually_test.append(p)

            # --- Testing ---
            if proxies_to_actually_test:
                # Respect max_proxies if set (global check approx)
                if max_proxies and stats.tested >= max_proxies:
                    logger.info("Max proxies limit reached.")
                    # Stop testing, but process what we have
                    pass
                else:
                    # Try batch testing first if available
                    if tester.go_tester.available:
                        # Process in chunks of 50 for the Go binary
                        chunk_size = 50
                        for i in range(0, len(proxies_to_actually_test), chunk_size):
                            chunk = proxies_to_actually_test[i : i + chunk_size]
                            # test_batch modifies proxies in-place
                            await tester.test_batch(chunk)

                            for res in chunk:
                                if res.is_working:
                                    final_batch_for_this_source.append(res)
                                    event_stream.emit(
                                        "test_success",
                                        f"Proxy working: {res.protocol}://{res.address}:{res.port} ({res.latency}ms)",
                                    )

                            stats.tested += len(chunk)
                            if progress and task_process:
                                progress.update(
                                    task_process,
                                    completed=stats.tested,
                                    description=f"[green]Testing... ({stats.working} working)",
                                )
                    else:
                        # Fallback to Legacy Loop
                        concurrency.start_tuner()

                        # Helper for concurrent testing
                        async def _test_wrap(p: Proxy):
                            sem = concurrency.get_semaphore()
                            async with sem:
                                res = await tester.test(p)
                                if res.is_working:
                                    event_stream.emit(
                                        "test_success",
                                        f"Proxy working: {res.protocol}://{res.address}:{res.port} ({res.latency}ms)",
                                    )
                                return res

                        # Chunk the tests to allow progress updates
                        chunk_size = 20
                        for i in range(0, len(proxies_to_actually_test), chunk_size):
                            chunk = proxies_to_actually_test[i : i + chunk_size]
                            results = await asyncio.gather(*[_test_wrap(x) for x in chunk])

                            for res in results:
                                await concurrency.record(
                                    "default", res.latency or 9999, res.is_working
                                )
                                if res.is_working:
                                    final_batch_for_this_source.append(res)

                            stats.tested += len(chunk)
                            if progress and task_process:
                                progress.update(
                                    task_process,
                                    completed=stats.tested,
                                    description=f"[green]Testing... ({stats.working} working)",
                                )

                        await concurrency.stop_tuner()

            # --- Post-Processing Working Proxies ---

            # Process proxies for geolocation and filtering
            for p in final_batch_for_this_source:
                if not p.is_working:
                    continue

                # Latency Filter
                if max_latency and (p.latency or 9999) > max_latency:
                    continue

                # Geolocation (if missing)
                # New GeoIP resolver handles caching internally
                if not p.country_code:
                    with tracker.phase("geo"):
                        geo_data = geoip.lookup(p.resolved_ip or p.address)
                        if geo_data.country_code:
                            p.country_code = geo_data.country_code
                            p.country = geo_data.country_code  # convention
                            p.city = geo_data.city
                            p.asn = geo_data.asn
                            p.org = geo_data.org
                        stats.geo_resolved += 1

                # Country Filter
                if country_filter:
                    if p.country_code != country_filter.upper():
                        continue

                final_proxies.append(p)
                stats.working += 1

            working_count = sum(1 for p in final_batch_for_this_source if p.is_working)
            fetched_count = len(parsed_batch)  # Total parsable

            # Calculate Diversity Score for this batch
            diversity_score = calculate_diversity_score(final_batch_for_this_source)

            # Update Quality Tracker (only for remote URLs, not local files)
            if not source.startswith("supplied-proxies") and not source.startswith(
                "sources/"
            ):
                quality_tracker.update(
                    source, fetched_count, working_count, diversity_score
                )

            work_queue.task_done()

    # 4. Execute Pipeline
    logger.info(f"Starting pipeline with {max_workers} initial workers")

    # Run Producer and Consumer concurrently
    producer_task = asyncio.create_task(_source_producer())
    consumer_task = asyncio.create_task(_processing_consumer())

    await asyncio.gather(producer_task, consumer_task)

    # 5. Final Cleanup & Output

    # Deduplicate Endpoints (IP:Port)
    # If we have multiple configs for same IP, keep best latency
    optimized_proxies = filter_unique_endpoints(final_proxies)

    # Sort by latency
    optimized_proxies.sort(key=lambda x: x.latency if x.latency else 9999)

    # Generate Outputs
    logger.info(f"Generating outputs for {len(optimized_proxies)} proxies...")
    event_stream.emit(
        "pipeline_finish",
        f"Pipeline finished. Generated {len(optimized_proxies)} proxies.",
    )

    # Ensure stats duration is set before metadata generation
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    stats.duration = float(duration)
    stats.final_count = len(optimized_proxies)

    # --- Integration of Proxy Washing ---
    # Wash proxies before generation to ensure consistent state across all outputs
    # This fixes the "Split Brain" issue where adapters didn't see washed proxies
    from .output import ProxyWasher

    washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))
    washed_outbounds = washer.wash_batch(optimized_proxies)

    generated_files = output.generate_categorized_outputs(
        optimized_proxies, output_path, washed_proxies=washed_outbounds
    )
    # Note: output.generate_categorized_outputs also handles split outputs and chains now.

    # NEW: Generate Metadata for Frontend
    output.save_metadata(stats.to_dict(), optimized_proxies, output_path)

    # New Adapters Exports
    try:
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
    # Use consolidated logic
    chosen_proxies = select_top_configs(
        optimized_proxies, top_per_protocol=50, total_limit=1000
    )
    chosen_dir = output_path / "chosen"
    chosen_dir.mkdir(exist_ok=True)

    (chosen_dir / "proxies.json").write_text(
        json.dumps([output.serialize_proxy(p) for p in chosen_proxies], indent=2)
    )
    (chosen_dir / "base64.txt").write_text(
        output.generate_base64_subscription(chosen_proxies)
    )

    # Save History & Cache
    history.save()
    test_cache.save()
    if timeout_tracker:
        timeout_tracker.save()

    return PipelineResult(success=True, stats=stats, output_files=generated_files)
