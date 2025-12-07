import asyncio
import logging
import orjson as json
from typing import List, Optional, Set, Dict

from rich.progress import Progress, TaskID

from ..models import Proxy
from ..auto_detect import auto_detect_and_parse as parse_config
from ..security_validator import (
    validate_batch_configs,
    STRICT_POLICY,
    TEST_POLICY,
    SecurityValidator,
)
from ..filtering import proxy_unique_key
from ..testers import SingBoxTester
from ..test_cache import TestResultCache
from ..scheduler import SmartRetestScheduler
from ..concurrency_manager import ConcurrencyManager
from ..geoip import GeoIPResolver
from ..source_quality import SourceQualityTracker, calculate_diversity_score
from ..performance import PerformanceTracker
from ..proxy_history import ProxyHistoryTracker
from .models import PipelineStats

if False:  # TYPE_CHECKING
    from ..event_stream import EventStream

logger = logging.getLogger(__name__)


async def processing_consumer(
    work_queue: asyncio.Queue,
    stats: PipelineStats,
    seen_keys: Set[tuple],
    final_proxies: List[Proxy],
    tester: SingBoxTester,
    scheduler: SmartRetestScheduler,
    test_cache: TestResultCache,
    concurrency: ConcurrencyManager,
    geoip: GeoIPResolver,
    tracker: PerformanceTracker,
    event_stream: Optional["EventStream"],
    quality_tracker: SourceQualityTracker,
    history: ProxyHistoryTracker,
    progress: Optional[Progress],
    task_process: Optional[TaskID],
    max_proxies: Optional[int],
    max_latency: Optional[int],
    country_filter: Optional[str],
    leniency: bool,
    seen_lock: Optional[asyncio.Lock] = None,
):
    policy = TEST_POLICY if leniency else STRICT_POLICY

    # Log tester status at start for debugging
    if tester.go_tester.available:
        logger.info("Using Go batch tester for proxy testing")
    else:
        logger.warning("Go batch tester unavailable - falling back to Python tester")

    # Fallback if lock not provided
    if seen_lock is None:
        seen_lock = asyncio.Lock()

    # [FIX] Do not start tuner here. It is managed by the orchestrator (pipeline.py)
    # to prevent race conditions and redundant toggling per consumer/batch.

    while True:
        try:
            # Add timeout to prevent indefinite blocking if producer dies
            # 600 seconds (10 minutes) to allow for slow sources/retries
            item = await asyncio.wait_for(work_queue.get(), timeout=600.0)
        except asyncio.TimeoutError:
            logger.warning("Consumer timed out waiting for work. Exiting.")
            break

        if item is None:
            work_queue.task_done()
            break

        # Unpack queue item: (source, raw_lines, metadata)
        if len(item) == 3:
            source, raw_lines, metadata = item
        else:
            source, raw_lines = item
            metadata = {}

        stats.fetched_sources += 1
        stats.fetched_lines += len(raw_lines)

        # Log metadata from fetcher if available
        fetch_meta_str = ""
        if metadata:
            fetch_dur = metadata.get("fetch_duration")
            if fetch_dur:
                fetch_meta_str = f" [Fetch: {fetch_dur * 1000:.0f}ms]"

        safe_source = SecurityValidator.sanitize_log_message(str(source))
        logger.info(
            f"Processing source {safe_source}: {len(raw_lines)} raw lines{fetch_meta_str}"
        )

        process_start_time = asyncio.get_running_loop().time()

        loop = asyncio.get_running_loop()

        def _parse_chunk(lines, src):
            result = []
            try:
                for i, line in enumerate(lines):
                    try:
                        p = parse_config(line)
                        if p:
                            p.details["_source"] = src
                            result.append(p)
                    except Exception as e:
                        logger.debug(
                            f"Parsing error for line {i} in {src}: {e}", exc_info=True
                        )
            except Exception as e:
                logger.error(
                    f"Fatal error in _parse_chunk for {src}: {e}", exc_info=True
                )
            return result

        parsed_batch = []
        with tracker.phase("parse"):
            parsed_batch = await loop.run_in_executor(
                None, _parse_chunk, raw_lines, source
            )

        if not parsed_batch:
            logger.warning(
                f"No valid proxies parsed from source {safe_source} "
                f"(Raw lines: {len(raw_lines)}). "
                f"Check parser logs/format compatibility."
            )
            work_queue.task_done()
            continue

        # Log protocol breakdown for parsed batch
        protocol_counts: Dict[str, int] = {}
        for p in parsed_batch:
            protocol_counts[p.protocol] = protocol_counts.get(p.protocol, 0) + 1
        logger.info(
            f"Parsed breakdown for {safe_source}: {json.dumps(protocol_counts).decode()}"
        )

        # [LOGGING] Trace parsing drop rate
        if len(parsed_batch) < len(raw_lines) * 0.5:
            logger.warning(
                f"Low parsing success rate for {safe_source}: {len(parsed_batch)}/{len(raw_lines)} lines parsed. "
                "Check for format changes or encoding issues."
            )

        unique_batch = []
        duplicates_count = 0
        # Deduplication logic.
        # Uses explicit lock to ensure safety if multiple consumers run concurrently.
        async with seen_lock:
            for p in parsed_batch:
                k = proxy_unique_key(p)
                if k not in seen_keys:
                    seen_keys.add(k)
                    unique_batch.append(p)
                else:
                    duplicates_count += 1

        stats.parsed += len(unique_batch)
        safe_source = SecurityValidator.sanitize_log_message(str(source))
        logger.debug(
            f"Starting security validation for {len(unique_batch)} proxies from {safe_source}..."
        )
        with tracker.phase("security_validation"):
            validation_start = loop.time()
            # Offload security validation to executor for batches > 100 to avoid blocking
            if len(unique_batch) > 100:
                safe_batch = await loop.run_in_executor(
                    None, validate_batch_configs, unique_batch, policy
                )
            else:
                safe_batch = validate_batch_configs(unique_batch, policy)
            validation_dur = (loop.time() - validation_start) * 1000

        dropped_unsafe = len(unique_batch) - len(safe_batch)
        if dropped_unsafe > 0:
            logger.warning(
                f"Security Filter [{safe_source}]: Dropped {dropped_unsafe} unsafe proxies in {validation_dur:.2f}ms. "
                f"Valid: {len(safe_batch)}/{len(unique_batch)} "
                f"(Retention: {len(safe_batch)/len(unique_batch):.1%})"
            )
            # [LOGGING] Log details of dropped proxies if useful
            if logger.isEnabledFor(logging.DEBUG):
                dropped_details = [
                    f"{p.protocol}://{p.address}"
                    for p in unique_batch
                    if p not in safe_batch
                ][:5]
                logger.debug(f"Sample dropped proxies: {dropped_details}...")
        else:
            safe_source = SecurityValidator.sanitize_log_message(str(source))
            logger.info(
                f"Security Filter [{safe_source}]: All {len(unique_batch)} proxies passed validation in {validation_dur:.2f}ms."
            )

        final_batch_for_this_source = []
        proxies_to_actually_test = []

        # Decide whether to reuse cached results or schedule a fresh test.
        # We treat any path that leads to an actual test as a cache miss
        # (including forced retests).
        cache_hits = 0
        forced_retests = 0
        for p in safe_batch:
            cached = None
            if not scheduler.should_retest(p):
                cached = test_cache.get(p)
            else:
                forced_retests += 1

            if cached:
                final_batch_for_this_source.append(cached)
                cache_hits += 1
            else:
                stats.cache_misses += 1
                proxies_to_actually_test.append(p)

        logger.info(
            f"Cache Check [{safe_source}]: {cache_hits} hits, {len(proxies_to_actually_test)} misses "
            f"(Forced Retests: {forced_retests}, Total: {len(safe_batch)})"
        )

        if proxies_to_actually_test:
            if max_proxies and stats.tested >= max_proxies:
                pass
            else:
                if tester.go_tester.available:
                    chunk_size = (
                        500  # Increased from 50 to reduce serialization overhead
                    )
                    for i in range(0, len(proxies_to_actually_test), chunk_size):
                        chunk = proxies_to_actually_test[i : i + chunk_size]
                        await tester.test_batch(chunk)
                        for res in chunk:
                            # Record history
                            # history.record_test_result(res) # ProxyHistoryTracker lacks this method

                            if res.is_working:
                                final_batch_for_this_source.append(res)
                                if event_stream:
                                    # Log only to DEBUG to avoid spamming main log
                                    logger.debug(
                                        f"Proxy working: {res.protocol}://{res.address}:{res.port} ({res.latency}ms)"
                                    )
                                    event_stream.emit(
                                        "test_success",
                                        f"Proxy working: {res.protocol}://{res.address}:{res.port} ({res.latency}ms)",
                                    )
                            else:
                                # Log failure for debugging transparency
                                # [LOGGING] Enhanced failure logging
                                error_msg = res.details.get("error", "unknown")
                                logger.debug(
                                    f"Proxy test failed [{safe_source}]: {res.protocol}://{res.address}:{res.port} - {error_msg}"
                                )
                        stats.tested += len(chunk)
                        # Log batch test summary
                        working_in_chunk = sum(1 for r in chunk if r.is_working)
                        logger.info(
                            f"Batch test result for {safe_source}: {working_in_chunk}/{len(chunk)} working "
                            f"({(working_in_chunk/len(chunk)*100):.1f}%)"
                        )
                        if working_in_chunk == 0 and len(chunk) > 0:
                            logger.warning(
                                f"Batch failure details for {safe_source}: All {len(chunk)} proxies failed in this chunk."
                            )

                        if progress and task_process:
                            progress.update(
                                task_process,
                                completed=stats.tested,
                                description=f"[green]Testing... ({stats.working} working)",
                            )
                else:
                    # Python fallback testing
                    async def _test_wrap(p: Proxy):
                        sem = concurrency.get_semaphore()
                        async with sem:
                            res = await tester.test(p)
                            if res.is_working:
                                if event_stream:
                                    # Log only to DEBUG to avoid spamming main log
                                    logger.debug(
                                        f"Proxy working: {res.protocol}://{res.address}:{res.port} ({res.latency}ms)"
                                    )
                                    event_stream.emit(
                                        "test_success",
                                        f"Proxy working: {res.protocol}://{res.address}:{res.port} ({res.latency}ms)",
                                    )
                            return res

                    # Process in chunks (increased from 50 to 100 for better throughput)
                    chunk_size = 100
                    for i in range(0, len(proxies_to_actually_test), chunk_size):
                        chunk = proxies_to_actually_test[i : i + chunk_size]
                        results = await asyncio.gather(*[_test_wrap(x) for x in chunk])
                        for res in results:
                            # Record history
                            # history.record_test_result(res) # ProxyHistoryTracker lacks this method

                            if res.is_working:
                                await concurrency.record(
                                    "default", res.latency or 0, True
                                )
                                final_batch_for_this_source.append(res)

                        stats.tested += len(chunk)
                        if progress and task_process:
                            progress.update(
                                task_process,
                                completed=stats.tested,
                                description=f"[green]Testing... ({stats.working} working)",
                            )

        for p in final_batch_for_this_source:
            if not p.is_working:
                continue
            if max_latency and (p.latency or 9999) > max_latency:
                continue
            if not p.country_code:
                with tracker.phase("geo"):
                    geo_data = geoip.lookup(p.resolved_ip or p.address)
                    if geo_data and geo_data.country_code:
                        # Ensure country_code is a normalized ISO code.
                        cc = geo_data.country_code or ""
                        p.country_code = cc
                        # Use human-readable country name when available,
                        # otherwise fall back to the ISO code.
                        p.country = geo_data.country_name or cc
                        p.city = geo_data.city or ""
                        p.asn = geo_data.asn or ""
                        p.org = geo_data.org or ""
                        if geo_data.lat:
                            p.details["lat"] = geo_data.lat
                        if geo_data.lng:
                            p.details["lng"] = geo_data.lng
                        stats.geo_resolved += 1
            if country_filter:
                if p.country_code != country_filter.upper():
                    continue
            final_proxies.append(p)
            stats.working += 1

        working_count = sum(1 for p in final_batch_for_this_source if p.is_working)
        fetched_count = len(parsed_batch)
        diversity_score = calculate_diversity_score(final_batch_for_this_source)

        process_end_time = asyncio.get_running_loop().time()
        total_duration = (process_end_time - process_start_time) * 1000  # ms
        fetch_duration = (
            metadata.get("fetch_duration") or 0.0
        ) * 1000  # convert s to ms
        full_duration_ms = total_duration + fetch_duration

        # Aggregate Failure Modes and GeoIP
        failure_modes: Dict[str, int] = {}
        geoip_stats: Dict[str, int] = {}

        for p in proxies_to_actually_test:
            if not p.is_working:
                error = p.details.get("error", "unknown")
                # Simplify error message
                if "timeout" in error.lower():
                    error_key = "timeout"
                elif "connection" in error.lower():
                    error_key = "connection_error"
                elif "dirty_ip" in error.lower() or "dirty ip" in error.lower():
                    error_key = "dirty_ip"
                elif "honeypot" in error.lower():
                    error_key = "honeypot"
                elif "handshake" in error.lower():
                    error_key = "handshake_fail"
                else:
                    error_key = "other"

                failure_modes[error_key] = failure_modes.get(error_key, 0) + 1

        for p in final_batch_for_this_source:
            if p.country_code:
                geoip_stats[p.country_code] = geoip_stats.get(p.country_code, 0) + 1

        # LOG SUMMARY FOR THIS SOURCE
        logger.info(
            f"Source Summary [{safe_source}]:\n"
            f"  Raw Lines:     {len(raw_lines)}\n"
            f"  Parsed:        {len(parsed_batch)}\n"
            f"  Unique:        {len(unique_batch)} (Dupes: {duplicates_count})\n"
            f"  Safe:          {len(safe_batch)} (Unsafe/Dropped: {dropped_unsafe})\n"
            f"  Tested:        {len(proxies_to_actually_test)} (Cached: {cache_hits})\n"
            f"  Working:       {working_count} (Success Rate: {(working_count/len(safe_batch)*100) if safe_batch else 0:.1f}%)\n"
            f"  Countries:     {json.dumps(geoip_stats).decode()}\n"
            f"  Duration:      {full_duration_ms:.0f}ms (Fetch: {fetch_duration:.0f}ms, Process: {total_duration:.0f}ms)"
        )

        if failure_modes:
            # Log failure modes at INFO level if significant failures occurred, otherwise DEBUG
            if working_count < len(safe_batch) * 0.5:
                logger.info(
                    f"Failure Breakdown [{safe_source}]: {json.dumps(failure_modes).decode()}"
                )
            else:
                logger.debug(
                    f"Failure Breakdown [{safe_source}]: {json.dumps(failure_modes).decode()}"
                )

        if not source.startswith("supplied-proxies") and not source.startswith(
            "sources/"
        ):
            try:
                await loop.run_in_executor(
                    None,
                    quality_tracker.update,
                    source,
                    fetched_count,
                    working_count,
                    diversity_score,
                    0.0,
                )
            except Exception as e:
                logger.warning(
                    f"Quality update failed for {safe_source}: {e}", exc_info=True
                )
            try:
                await loop.run_in_executor(
                    None,
                    quality_tracker.record_run,
                    source,
                    {
                        "timestamp": int(process_end_time),
                        "duration_ms": full_duration_ms,
                        "fetched_count": fetched_count,
                        "working_count": working_count,
                        "geoip_json": json.dumps(geoip_stats).decode(),
                        "failure_modes_json": json.dumps(failure_modes).decode(),
                        "batch_source": "pipeline",
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Quality record_run failed for {safe_source}: {e}", exc_info=True
                )
        else:
            # [LOGGING] Log for local/manual sources too
            logger.info(
                f"Completed processing for local source {safe_source} - "
                f"Fetch/Parse/Work: {len(raw_lines)}/{len(parsed_batch)}/{working_count}"
            )

        work_queue.task_done()

    # After all processing (outside the loop)
    if stats.tested > 0 and stats.working == 0:
        logger.error(
            f"CRITICAL: All {stats.tested} proxy tests failed across all sources! "
            f"This likely indicates: 1) Go tester not available, "
            f"2) Network connectivity issues to test URLs, or "
            f"3) All proxy configurations are invalid/incompatible."
        )
