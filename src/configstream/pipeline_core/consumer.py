import asyncio
import logging
import os
import orjson as json
from typing import List, Optional, Any, TYPE_CHECKING

from rich.progress import Progress, TaskID

from configstream.models import Proxy
from configstream.auto_detect import auto_detect_and_parse as parse_config
from configstream.security_validator import (
    validate_batch_configs,
    STRICT_POLICY,
    TEST_POLICY,
    SecurityValidator,
)
from configstream.filtering import proxy_unique_key
from configstream.testers import SingBoxTester
from configstream.test_cache import TestResultCache
from configstream.scheduler import SmartRetestScheduler
from configstream.concurrency_manager import ConcurrencyManager
from configstream.geoip import GeoIPResolver
from configstream.source_quality import SourceQualityTracker, calculate_diversity_score
from configstream.performance import PerformanceTracker
from configstream.history.tracker import ProxyHistoryTracker
from configstream.pipeline_core.models import PipelineStats
from configstream.intelligence.washer.core import ProxyWasher

if TYPE_CHECKING:
    from configstream.event_stream import EventStream

logger = logging.getLogger(__name__)


async def processing_consumer(
    work_queue: asyncio.Queue,
    stats: PipelineStats,
    seen_keys: Any,  # Expects Dict or Set
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
    washer: Optional[ProxyWasher] = None,  # [FIX] Receive shared washer
):
    policy = TEST_POLICY if leniency else STRICT_POLICY

    if tester.go_tester.available:
        logger.info("Using Go batch tester for proxy testing")
    else:
        logger.warning("Go batch tester unavailable - falling back to Python tester")

    if seen_lock is None:
        seen_lock = asyncio.Lock()

    # [FIX] Use passed shared washer or fallback (legacy support)
    if washer is None:
        washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))
        await washer.fetch_clean_ips()

    while True:
        # The producer sends None as sentinel when done, which is the proper
        # termination mechanism. A timeout could cause premature exit if sources
        # are slow to fetch, leading to incomplete processing and lost data.
        item = await work_queue.get()

        if item is None:
            work_queue.task_done()
            break

        if len(item) == 3:
            source, raw_lines, metadata = item
        else:
            source, raw_lines = item
            metadata = {}

        async with seen_lock:
            stats.fetched_sources += 1
            stats.fetched_lines += len(raw_lines)
            if "drop_stats" in metadata and isinstance(metadata["drop_stats"], dict):
                for reason, count in metadata["drop_stats"].items():
                    stats.drop_reasons[reason] = (
                        stats.drop_reasons.get(reason, 0) + count
                    )

        fetch_meta_str = ""
        if metadata:
            fetch_dur = metadata.get("fetch_duration")
            if fetch_dur:
                fetch_meta_str = f" [Fetch: {fetch_dur * 1000:.0f}ms]"

        safe_source = SecurityValidator.sanitize_log_message(str(source))
        logger.debug(
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
                    except Exception:
                        pass
            except Exception:
                pass
            return result

        parsed_batch = []
        with tracker.phase("parse"):
            parsed_batch = await loop.run_in_executor(
                None, _parse_chunk, raw_lines, source
            )

        if not parsed_batch:
            work_queue.task_done()
            continue

        unique_batch = []
        duplicates_count = 0
        async with seen_lock:
            # Use more efficient deduplication (LRU style)
            max_seen = int(os.getenv("MAX_SEEN_KEYS", "200000"))

            for p in parsed_batch:
                k = proxy_unique_key(p)
                if k not in seen_keys:
                    # If approaching limit, remove oldest entries
                    if len(seen_keys) >= max_seen:
                        eviction_count = max(100, max_seen // 100)  # Evict 1%

                        # Dict: Iterating gives insertion order (oldest first)
                        # We enforce seen_keys to be a Dict in pipeline.py
                        it = iter(seen_keys)
                        for _ in range(eviction_count):
                            try:
                                del seen_keys[next(it)]
                            except (StopIteration, KeyError, RuntimeError):
                                break

                    seen_keys[k] = None  # Add to dict
                    unique_batch.append(p)
                else:
                    duplicates_count += 1
            stats.drop_reasons["duplicate"] = (
                stats.drop_reasons.get("duplicate", 0) + duplicates_count
            )

        async with seen_lock:
            stats.parsed += len(unique_batch)

        with tracker.phase("security_validation"):
            if len(unique_batch) > 100:
                safe_batch = await loop.run_in_executor(
                    None, validate_batch_configs, unique_batch, policy
                )
            else:
                safe_batch = validate_batch_configs(unique_batch, policy)

        dropped_unsafe = len(unique_batch) - len(safe_batch)
        if dropped_unsafe > 0:
            async with seen_lock:
                stats.drop_reasons["security_validation"] = (
                    stats.drop_reasons.get("security_validation", 0) + dropped_unsafe
                )

        final_batch_for_this_source = []
        proxies_to_actually_test = []

        # Cache Check
        for p in safe_batch:
            cached = None
            if not scheduler.should_retest(p):
                cached = test_cache.get(p)

            if cached:
                final_batch_for_this_source.append(cached)
            else:
                async with seen_lock:
                    stats.cache_misses += 1
                proxies_to_actually_test.append(p)

        # Testing
        failed_proxies = []  # Candidates for revival

        if proxies_to_actually_test:
            if max_proxies and stats.tested >= max_proxies:
                pass
            else:
                if tester.go_tester.available:
                    chunk_size = int(os.getenv("GO_TESTER_BATCH_SIZE", "200"))
                    for i in range(0, len(proxies_to_actually_test), chunk_size):
                        chunk = proxies_to_actually_test[i : i + chunk_size]
                        await tester.test_batch(chunk)
                        for res in chunk:
                            history.record_test_result(res)
                            if res.is_working:
                                res.process = "native"  # Explicitly mark as native
                                final_batch_for_this_source.append(res)
                            else:
                                # [REVIVAL] Collect failed proxies
                                failed_proxies.append(res)

                                failure_cat = res.details.get(
                                    "failure_category", "TEST_FAILED"
                                )
                                async with seen_lock:
                                    stats.drop_reasons[failure_cat] = (
                                        stats.drop_reasons.get(failure_cat, 0) + 1
                                    )

                        async with seen_lock:
                            stats.tested += len(chunk)

                        if progress and task_process:
                            progress.update(task_process, completed=stats.tested)
                else:
                    # Python fallback testing
                    chunk_size = int(os.getenv("PY_TESTER_BATCH_SIZE", "100"))
                    for i in range(0, len(proxies_to_actually_test), chunk_size):
                        chunk = proxies_to_actually_test[i : i + chunk_size]

                        async def _test_wrap(p: Proxy):
                            sem = concurrency.get_semaphore()
                            async with sem:
                                return await tester.test(p)

                        results = await asyncio.gather(*[_test_wrap(x) for x in chunk])
                        for res in results:
                            history.record_test_result(res)
                            if res.is_working:
                                res.process = "native"
                                await concurrency.record(
                                    "default", res.latency or 0, True
                                )
                                final_batch_for_this_source.append(res)
                            else:
                                failed_proxies.append(res)  # Collect for revival
                                error = res.details.get("error", "TEST_FAILED")
                                async with seen_lock:
                                    stats.drop_reasons[error] = (
                                        stats.drop_reasons.get(error, 0) + 1
                                    )

                        async with seen_lock:
                            stats.tested += len(chunk)
                        if progress and task_process:
                            progress.update(task_process, completed=stats.tested)

        # --- REVIVAL LOOP ---
        if failed_proxies:
            # 1. Attempt Vwarp Revival (Priority)
            vwarp_candidates, _ = washer.wash_failed(
                failed_proxies, stats=stats, use_vwarp=True
            )
            if vwarp_candidates:
                # Test Vwarp Candidates
                await tester.test_batch(vwarp_candidates)
                for p in vwarp_candidates:
                    if p.is_working:
                        p.process = "revived-vwarp"
                        # Recover origin info
                        origin = p.details.get("origin_proxy")
                        if origin:
                            p.country_code = origin.country_code
                            p.country = origin.country
                        final_batch_for_this_source.append(p)
                        async with seen_lock:
                            stats.revived_vwarp += 1

            # 2. Attempt Standard Warp Revival (Fallback/Parallel)
            # Filter out those that already succeeded via Vwarp?
            # Or just try everything? Let's try remaining failed ones or all.
            # For simplicity and coverage, we can try both strategies on the original failed set.
            warp_candidates, _ = washer.wash_failed(
                failed_proxies, stats=stats, use_vwarp=False
            )
            if warp_candidates:
                await tester.test_batch(warp_candidates)
                for p in warp_candidates:
                    if p.is_working:
                        p.process = "revived-warp"
                        origin = p.details.get("origin_proxy")
                        if origin:
                            p.country_code = origin.country_code
                            p.country = origin.country
                        final_batch_for_this_source.append(p)
                        async with seen_lock:
                            stats.revived_warp += 1

        # Post-process final batch (GeoIP, Filter)
        for p in final_batch_for_this_source:
            if not p.is_working:
                continue
            if max_latency and (p.latency or 9999) > max_latency:
                continue
            if not p.country_code:
                with tracker.phase("geo"):
                    geo_data = await geoip.lookup(p.resolved_ip or p.address)
                    if geo_data and geo_data.country_code:
                        cc = geo_data.country_code or ""
                        p.country_code = cc
                        p.country = geo_data.country_name or cc
                        p.city = geo_data.city or ""
                        p.asn = geo_data.asn or ""
                        p.org = geo_data.org or ""
                        if geo_data.lat:
                            p.details["lat"] = geo_data.lat
                        if geo_data.lng:
                            p.details["lng"] = geo_data.lng
                        async with seen_lock:
                            stats.geo_resolved += 1
            if country_filter:
                if p.country_code != country_filter.upper():
                    continue
            # Fix: Acquire lock before appending to prevent race condition
            async with seen_lock:
                final_proxies.append(p)
                stats.working += 1

        working_count = sum(1 for p in final_batch_for_this_source if p.is_working)
        fetched_count = len(parsed_batch)
        diversity_score = calculate_diversity_score(final_batch_for_this_source)

        process_end_time = asyncio.get_running_loop().time()
        total_duration = (process_end_time - process_start_time) * 1000
        fetch_duration = (metadata.get("fetch_duration") or 0.0) * 1000
        full_duration_ms = total_duration + fetch_duration

        # Aggregate Failure Modes & GeoIP for logging
        failure_modes: dict = {}  # Already aggregated into stats, local dict for log
        geoip_stats: dict = {}
        for p in final_batch_for_this_source:
            if p.country_code:
                geoip_stats[p.country_code] = geoip_stats.get(p.country_code, 0) + 1

        summary_msg = (
            f"Source Summary [{safe_source}]: "
            f"Raw={len(raw_lines)} "
            f"Parsed={len(parsed_batch)} "
            f"Tested={len(proxies_to_actually_test)} "
            f"Working={working_count} "
            f"Dur={full_duration_ms:.0f}ms"
        )

        if working_count > 0:
            logger.info(summary_msg)
        else:
            logger.debug(summary_msg)

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
            except Exception:
                pass
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
            except Exception:
                pass

        work_queue.task_done()

    if stats.tested > 0 and stats.working == 0:
        logger.error(
            f"CRITICAL: All {stats.tested} proxy tests failed across all sources!"
        )
