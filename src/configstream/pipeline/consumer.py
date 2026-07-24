# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import inspect
import time
import hashlib
from pathlib import Path
import orjson as json
from typing import List, Optional, Any, TYPE_CHECKING, cast, Dict

from rich.progress import Progress, TaskID

from configstream.models import Proxy
import configstream.consumer as consumer_mod
from configstream.security_validator import (
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
from configstream.pipeline_stats import PipelineStats
from configstream.intelligence.washer.core import ProxyWasher
from configstream.config import AppSettings
from configstream.pipeline.interfaces import IConsumer
from configstream.pipeline.models import PipelineContext

if TYPE_CHECKING:
    from configstream.event_stream import EventStream
    from configstream.utils.bloom import BloomFilter

logger = logging.getLogger(__name__)


class WorkerConsumer(IConsumer):
    def __init__(self, context: PipelineContext, worker_id: int):
        self.context = context
        self.worker_id = worker_id

    async def consume(self) -> None:
        import configstream.pipeline

        # Contract: the pipeline core always provides these collaborators.
        ctx = self.context
        required = {
            "tester": ctx.tester,
            "scheduler": ctx.scheduler,
            "test_cache": ctx.test_cache,
            "concurrency": ctx.concurrency,
            "geoip": ctx.geoip,
            "tracker": ctx.tracker,
            "quality_tracker": ctx.quality_tracker,
            "history": ctx.history,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise RuntimeError(
                "PipelineContext is missing required collaborators for "
                f"WorkerConsumer: {', '.join(missing)}"
            )

        tester = cast(SingBoxTester, ctx.tester)
        scheduler = cast(SmartRetestScheduler, ctx.scheduler)
        test_cache = cast(TestResultCache, ctx.test_cache)
        concurrency = cast(ConcurrencyManager, ctx.concurrency)
        geoip = cast(GeoIPResolver, ctx.geoip)
        tracker = cast(PerformanceTracker, ctx.tracker)
        quality_tracker = cast(SourceQualityTracker, ctx.quality_tracker)
        history = cast(ProxyHistoryTracker, ctx.history)

        await configstream.pipeline.processing_consumer(
            ctx.work_queue,
            ctx.stats,
            ctx.seen_keys,
            ctx.final_proxies,
            tester,
            scheduler,
            test_cache,
            concurrency,
            geoip,
            tracker,
            ctx.event_stream,
            quality_tracker,
            history,
            ctx.progress,
            ctx.task_process,
            ctx.max_latency,
            ctx.country_filter,
            ctx.leniency,
            consumer_id=self.worker_id,
            seen_lock=ctx.seen_lock,
            washer=ctx.washer,
            stop_event=ctx.stop_event,
            seen_bloom=ctx.seen_bloom,
        )


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
    max_latency: Optional[int],
    country_filter: Optional[str],
    leniency: bool,
    consumer_id: int = 0,
    seen_lock: Optional[asyncio.Lock] = None,
    washer: Optional[ProxyWasher] = None,  # Receive shared washer
    stop_event: Optional[asyncio.Event] = None,
    seen_bloom: Optional["BloomFilter"] = None,
):
    settings = AppSettings()
    policy = TEST_POLICY if leniency else STRICT_POLICY
    policy = policy.copy()
    policy["allow_local_ips"] = settings.ALLOW_PRIVATE_IPS
    policy["require_tls_validation"] = settings.TLS_TESTS_ENABLED
    enable_cache_warming = settings.ENABLE_CACHE_WARMING

    if seen_lock is None:
        seen_lock = asyncio.Lock()

    if stop_event is None:
        stop_event = asyncio.Event()

    # Use passed shared washer or create default
    if washer is None:
        washer = ProxyWasher(AppSettings().WARP_KEY_POOL)
    washer_ready = False

    while True:
        # The producer sends None as sentinel when done, which is the proper
        # termination mechanism. A timeout could cause premature exit if sources
        # are slow to fetch, leading to incomplete processing and lost data.
        item = await work_queue.get()

        if item is None:
            work_queue.task_done()
            break

        if stop_event.is_set():
            work_queue.task_done()
            continue

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
            safe_src = SecurityValidator.sanitize_log_message(str(src))
            for i, line in enumerate(lines):
                try:
                    p = consumer_mod.parse_config(line)
                    if p:
                        p.details["_source"] = src
                        result.append(p)
                except Exception as e:
                    safe_error = SecurityValidator.sanitize_log_message(str(e))
                    logger.debug(
                        f"Parse error for source {safe_src} (line {i}): {safe_error}"
                    )
            return result

        parsed_batch = []
        with tracker.phase("parse"):
            parsed_batch = await loop.run_in_executor(
                None, _parse_chunk, raw_lines, source
            )

        if not parsed_batch:
            work_queue.task_done()
            continue

        # [FINGERPRINT] Save source fingerprint for similarity analysis
        def _save_fingerprint(batch, src_url):
            try:
                fingerprint_keys = []
                for p in batch:
                    k = proxy_unique_key(p)
                    fingerprint_keys.append(k)

                fingerprint_set = list(set(fingerprint_keys))

                if fingerprint_set:
                    src_hash = hashlib.sha256(
                        src_url.encode("utf-8", errors="ignore")
                    ).hexdigest()
                    fp_dir = Path("data") / "fingerprints"
                    fp_dir.mkdir(parents=True, exist_ok=True)
                    fp_file = fp_dir / f"{src_hash}.json"

                    fp_data = {
                        "url": SecurityValidator.sanitize_log_message(str(src_url)),
                        "proxies": fingerprint_set,
                        "timestamp": int(time.time()),
                    }

                    tmp_fp = fp_file.with_suffix(".tmp")
                    raw = json.dumps(fp_data)
                    tmp_fp.write_bytes(
                        raw if isinstance(raw, bytes) else raw.encode("utf-8")
                    )
                    tmp_fp.replace(fp_file)
            except Exception as e:
                logger.debug(f"Fingerprint save failed: {e}")

        await loop.run_in_executor(None, _save_fingerprint, parsed_batch, source)

        # 1. Deduplication Stage
        async with seen_lock:
            unique_batch, duplicates_count = _deduplicate_batch(
                parsed_batch, seen_keys, seen_bloom, settings
            )
            stats.drop_reasons["duplicate"] = (
                stats.drop_reasons.get("duplicate", 0) + duplicates_count
            )
            stats.parsed += len(unique_batch)

        # 2. Security Validation & Cache Warming
        safe_batch = await _validate_and_warm_cache(
            unique_batch, policy, enable_cache_warming, test_cache, loop, tracker
        )

        dropped_unsafe = len(unique_batch) - len(safe_batch)
        if dropped_unsafe > 0:
            async with seen_lock:
                stats.drop_reasons["security_validation"] = (
                    stats.drop_reasons.get("security_validation", 0) + dropped_unsafe
                )

        # 3. Candidate Testing Stage
        (
            final_batch_for_this_source,
            failed_proxies,
            tested_count,
        ) = await _test_candidates(
            safe_batch,
            tester,
            scheduler,
            test_cache,
            concurrency,
            history,
            stats,
            seen_lock,
            loop,
            progress,
            task_process,
            settings,
        )

        # 4. Proxy Revival Loop
        if failed_proxies:
            if not tester.go_tester.available:
                logger.info(
                    "Skipping proxy revival (WARP) because Go tester is unavailable."
                )
            else:
                if not washer_ready or not washer.clean_ips or not washer.warp_keys:
                    fetch_clean = getattr(washer, "fetch_clean_ips", None)
                    if callable(fetch_clean):
                        result = fetch_clean()
                        if inspect.isawaitable(result):
                            await result
                    washer_ready = True

                await _revive_failed_proxies(
                    failed_proxies,
                    tester,
                    washer,
                    settings,
                    stats,
                    seen_lock,
                    final_batch_for_this_source,
                )

        # 5. GeoIP Enrichment & Latency/Country Filtering
        working_count = await _enrich_geoip_and_filter(
            final_batch_for_this_source,
            geoip,
            tracker,
            stats,
            seen_lock,
            country_filter,
            max_latency,
            final_proxies,
        )

        # 6. Source Metrics Reporting
        fetched_count = len(parsed_batch)
        diversity_score = calculate_diversity_score(final_batch_for_this_source)

        process_end_time = asyncio.get_running_loop().time()
        total_duration = (process_end_time - process_start_time) * 1000
        fetch_duration = (metadata.get("fetch_duration") or 0.0) * 1000
        full_duration_ms = total_duration + fetch_duration

        # Aggregate Failure Modes & GeoIP for logging
        failure_modes: dict = {}
        if metadata and isinstance(metadata.get("drop_stats"), dict):
            failure_modes.update(metadata.get("drop_stats", {}))
        geoip_stats: dict = {}
        for p in final_batch_for_this_source:
            if p.country_code:
                geoip_stats[p.country_code] = geoip_stats.get(p.country_code, 0) + 1

        summary_msg = (
            f"Source Summary [{safe_source}]: "
            f"Raw={len(raw_lines)} "
            f"Parsed={len(parsed_batch)} "
            f"Tested={tested_count} "
            f"Working={working_count} "
            f"Dur={full_duration_ms:.0f}ms"
        )

        if working_count > 0:
            logger.info(summary_msg)
        else:
            logger.warning("(No proxies passed) " + summary_msg)

        if (
            not source.startswith("supplied-proxies")
            and not source.startswith("supplied-config")
            and not source.startswith("sources/")
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
            except Exception:  # nosec B110
                logging.getLogger(__name__).debug("Suppressed broad exception")
                pass
            try:
                batch_number = str(getattr(settings, "BATCH_NUMBER", "")).strip()
                batch_source = f"batch_{batch_number}" if batch_number else "pipeline"
                await loop.run_in_executor(
                    None,
                    quality_tracker.record_run,
                    source,
                    {
                        "timestamp": int(time.time()),
                        "duration_ms": full_duration_ms,
                        "fetched_count": fetched_count,
                        "working_count": working_count,
                        "geoip_json": json.dumps(geoip_stats).decode(),
                        "failure_modes_json": json.dumps(failure_modes).decode(),
                        "batch_source": batch_source,
                    },
                )
            except Exception:  # nosec B110
                logging.getLogger(__name__).debug("Suppressed broad exception")
                pass

        work_queue.task_done()

    if consumer_id == 0 and stats.tested > 0 and stats.working == 0:
        logger.error(
            f"CRITICAL: All {stats.tested} proxy tests failed across all sources!"
        )


def _deduplicate_batch(
    parsed_batch: List[Proxy],
    seen_keys: Any,
    seen_bloom: Optional["BloomFilter"],
    settings: AppSettings,
) -> tuple[List[Proxy], int]:
    """Deduplicate parsed proxies using BloomFilter or set/dict fallback."""
    unique_batch = []
    duplicates_count = 0

    def _to_bloom_key(unique_key: Any) -> str:
        if isinstance(unique_key, tuple):
            return "|".join(str(part) for part in unique_key)
        return str(unique_key)

    if seen_bloom is not None:
        for p in parsed_batch:
            k = proxy_unique_key(p)
            bloom_key = _to_bloom_key(k)
            if bloom_key in seen_bloom:
                duplicates_count += 1
                continue
            seen_bloom.add(bloom_key)
            unique_batch.append(p)
    else:
        # Fallback exact dedupe with optional bounded memory.
        max_seen = settings.MAX_SEEN_KEYS
        for p in parsed_batch:
            k = proxy_unique_key(p)
            if k not in seen_keys:
                if max_seen > 0 and len(seen_keys) >= max_seen:
                    eviction_count = max(1000, max_seen // 10)
                    if isinstance(seen_keys, dict):
                        keys_to_remove = []
                        it = iter(seen_keys)
                        try:
                            for _ in range(eviction_count):
                                keys_to_remove.append(next(it))
                        except StopIteration:
                            pass
                        for k_rm in keys_to_remove:
                            seen_keys.pop(k_rm, None)
                    elif isinstance(seen_keys, set):
                        for _ in range(eviction_count):
                            try:
                                seen_keys.pop()
                            except KeyError:
                                break

                if isinstance(seen_keys, dict):
                    seen_keys[k] = None
                elif isinstance(seen_keys, set):
                    seen_keys.add(k)
                unique_batch.append(p)
            else:
                duplicates_count += 1

    return unique_batch, duplicates_count


async def _validate_and_warm_cache(
    unique_batch: List[Proxy],
    policy: Dict[str, Any],
    enable_cache_warming: bool,
    test_cache: TestResultCache,
    loop: asyncio.AbstractEventLoop,
    tracker: PerformanceTracker,
) -> List[Proxy]:
    """Validate configs and perform cache warming."""
    with tracker.phase("security_validation"):
        if len(unique_batch) > 100:
            safe_batch = await loop.run_in_executor(
                None, consumer_mod.validate_batch_configs, unique_batch, policy
            )
        else:
            safe_batch = consumer_mod.validate_batch_configs(unique_batch, policy)

    if enable_cache_warming and safe_batch:
        try:
            from configstream.cache_warming import warm_cache

            safe_batch = warm_cache(test_cache, safe_batch)
        except Exception as exc:
            logger.debug(
                SecurityValidator.sanitize_log_message(
                    f"Cache warming skipped due to error: {exc}"
                )
            )
    return safe_batch


async def _test_candidates(
    safe_batch: List[Proxy],
    tester: SingBoxTester,
    scheduler: SmartRetestScheduler,
    test_cache: TestResultCache,
    concurrency: ConcurrencyManager,
    history: ProxyHistoryTracker,
    stats: PipelineStats,
    seen_lock: asyncio.Lock,
    loop: asyncio.AbstractEventLoop,
    progress: Optional[Progress],
    task_process: Optional[TaskID],
    settings: AppSettings,
) -> tuple[List[Proxy], List[Proxy], int]:
    """Test candidate proxies using Go tester daemon or Python fallback."""
    final_batch_for_this_source = []
    proxies_to_actually_test = []

    # Cache Check (batch lock acquisition instead of per-proxy)
    _local_cache_misses = 0
    for p in safe_batch:
        cached = None
        if not scheduler.should_retest(p):
            cached = test_cache.get(p)

        if cached:
            final_batch_for_this_source.append(cached)
        else:
            _local_cache_misses += 1
            proxies_to_actually_test.append(p)

    if _local_cache_misses:
        async with seen_lock:
            stats.cache_misses += _local_cache_misses

    failed_proxies = []
    tested_count = len(proxies_to_actually_test)

    if proxies_to_actually_test:
        if tester.go_tester.available:
            # Clamp chunk size to avoid overwhelming Go tester
            if settings.GO_TESTER_BATCH_SIZE <= 0:
                chunk_size = len(proxies_to_actually_test)
            else:
                chunk_size = max(1, int(settings.GO_TESTER_BATCH_SIZE))

            for i in range(0, len(proxies_to_actually_test), chunk_size):
                chunk = proxies_to_actually_test[i : i + chunk_size]
                try:
                    await tester.test_batch(chunk)
                except Exception as e:
                    logger.error(
                        SecurityValidator.sanitize_log_message(
                            f"Go batch tester failed for chunk: {e}. Fallback to Python tester."
                        )
                    )
                    # Record batch error in stats so metadata reflects the failure
                    async with seen_lock:
                        stats.drop_reasons["tester_error"] = stats.drop_reasons.get(
                            "tester_error", 0
                        ) + len(chunk)

                    # Fallback to Python tester for this chunk
                    async def _fallback_test(p: Proxy):
                        sem = concurrency.get_semaphore()
                        async with sem:
                            try:
                                return await tester.test(p)
                            except asyncio.CancelledError:
                                raise
                            except Exception as e:
                                logger.error(
                                    SecurityValidator.sanitize_log_message(
                                        f"Fallback test failed for proxy {p.id}: {e}"
                                    )
                                )
                                p.is_working = False
                                p.details["error"] = "FALLBACK_TEST_FAILED"
                                return p

                    results = await asyncio.gather(
                        *[_fallback_test(x) for x in chunk],
                        return_exceptions=True,
                    )
                    for idx, res in enumerate(results):
                        if isinstance(res, Proxy):
                            chunk[idx] = res
                        else:
                            if isinstance(res, asyncio.CancelledError):
                                raise res

                            p = chunk[idx]
                            p.is_working = False
                            p.details["error"] = "FALLBACK_TEST_EXCEPTION"
                            logger.error(
                                SecurityValidator.sanitize_log_message(
                                    f"Fallback test for proxy {p.id} raised an exception: {res}"
                                )
                            )

                # Batch history update in executor to prevent blocking loop
                if chunk:
                    await loop.run_in_executor(None, history.update_history, chunk)

                for res in chunk:
                    if res.is_working:
                        res.process = "native"  # Explicitly mark as native
                        final_batch_for_this_source.append(res)
                    else:
                        failed_proxies.append(res)
                        failure_cat = res.details.get("failure_category", "TEST_FAILED")
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
            if settings.PY_TESTER_BATCH_SIZE <= 0:
                chunk_size = len(proxies_to_actually_test)
            else:
                chunk_size = max(1, int(settings.PY_TESTER_BATCH_SIZE))
            for i in range(0, len(proxies_to_actually_test), chunk_size):
                chunk = proxies_to_actually_test[i : i + chunk_size]

                async def _test_wrap(p: Proxy):
                    sem = concurrency.get_semaphore()
                    async with sem:
                        return await tester.test(p)

                results = await asyncio.gather(*[_test_wrap(x) for x in chunk])

                # Batch history update in executor
                if results:
                    await loop.run_in_executor(
                        None, history.update_history, list(results)
                    )

                for res in results:
                    if res.is_working:
                        res.process = "native"
                        await concurrency.record("default", res.latency or 0, True)
                        final_batch_for_this_source.append(res)
                    else:
                        failed_proxies.append(res)
                        error = res.details.get("error", "TEST_FAILED")
                        async with seen_lock:
                            stats.drop_reasons[error] = (
                                stats.drop_reasons.get(error, 0) + 1
                            )
                        # Record failure for concurrency tuning feedback
                        await concurrency.record("default", res.latency or 0, False)

                async with seen_lock:
                    stats.tested += len(chunk)
                if progress and task_process:
                    progress.update(task_process, completed=stats.tested)

    return final_batch_for_this_source, failed_proxies, tested_count


async def _revive_failed_proxies(
    failed_proxies: List[Proxy],
    tester: SingBoxTester,
    washer: ProxyWasher,
    settings: AppSettings,
    stats: PipelineStats,
    seen_lock: asyncio.Lock,
    final_batch_for_this_source: List[Proxy],
) -> None:
    """Attempt proxy revival (Vwarp / Standard Warp)."""
    # 1. Attempt Vwarp Revival (Priority)
    vwarp_candidates: List[Proxy] = []
    vwarp_available = False
    _async_vwarp_check = getattr(washer, "is_vwarp_available_async", None)
    if callable(_async_vwarp_check):
        _check_result = _async_vwarp_check()
        if inspect.isawaitable(_check_result):
            vwarp_available = bool(await _check_result)
        else:
            vwarp_available = bool(_check_result)
    else:
        _sync_vwarp_check = getattr(washer, "is_vwarp_available", None)
        if callable(_sync_vwarp_check):
            vwarp_available = bool(_sync_vwarp_check())

    if settings.USE_VWARP_TUNNEL and washer.warp_keys and vwarp_available:
        vwarp_candidates, _ = washer.wash_failed(
            failed_proxies, stats=stats, use_vwarp=True
        )

    vwarp_success_ids: set[str] = set()
    if vwarp_candidates:
        try:
            await tester.test_batch(vwarp_candidates)
        except Exception as e:
            logger.error(
                SecurityValidator.sanitize_log_message(f"Vwarp batch test failed: {e}")
            )
            async with seen_lock:
                stats.drop_reasons["tester_error"] = stats.drop_reasons.get(
                    "tester_error", 0
                ) + len(vwarp_candidates)

        for p in vwarp_candidates:
            p.process = "revived-vwarp"
            if "revived-vwarp" not in p.tags:
                p.tags.append("revived-vwarp")
            origin = p.details.get("origin_proxy")
            if origin:
                p.country_code = origin.get("country_code", "")
                p.country = origin.get("country", "")
            origin_id = p.details.get("origin_id")
            origin_key = p.details.get("_origin_key")
            if p.is_working:
                if origin_id:
                    vwarp_success_ids.add(str(origin_id))
                if origin_key:
                    vwarp_success_ids.add(str(origin_key))
            final_batch_for_this_source.append(p)
            if p.is_working:
                async with seen_lock:
                    stats.revived_vwarp += 1
                    stats.vwarp_success += 1

    # 2. Attempt Standard Warp Revival (Fallback)
    from ...filtering import proxy_unique_key

    remaining_failed = (
        [
            fp
            for fp in failed_proxies
            if str(fp.id) not in vwarp_success_ids
            and str(proxy_unique_key(fp)) not in vwarp_success_ids
        ]
        if vwarp_success_ids
        else list(failed_proxies)
    )

    if remaining_failed:
        warp_candidates, _ = washer.wash_failed(
            remaining_failed, stats=stats, use_vwarp=False
        )
        if warp_candidates:
            try:
                await tester.test_batch(warp_candidates)
            except Exception as e:
                logger.error(
                    SecurityValidator.sanitize_log_message(
                        f"WARP batch test failed: {e}"
                    )
                )
                async with seen_lock:
                    stats.drop_reasons["tester_error"] = stats.drop_reasons.get(
                        "tester_error", 0
                    ) + len(warp_candidates)
            for p in warp_candidates:
                p.process = "revived-warp"
                if "revived-warp" not in p.tags:
                    p.tags.append("revived-warp")
                origin = p.details.get("origin_proxy")
                if origin:
                    p.country_code = origin.get("country_code", "")
                    p.country = origin.get("country", "")
                final_batch_for_this_source.append(p)
                if p.is_working:
                    async with seen_lock:
                        stats.revived_warp += 1


async def _enrich_geoip_and_filter(
    final_batch_for_this_source: List[Proxy],
    geoip: GeoIPResolver,
    tracker: PerformanceTracker,
    stats: PipelineStats,
    seen_lock: asyncio.Lock,
    country_filter: Optional[str],
    max_latency: Optional[int],
    final_proxies: List[Proxy],
) -> int:
    """Enrich proxies with GeoIP information and apply final filtering."""
    local_working_count = 0
    for p in final_batch_for_this_source:
        # GeoIP enrichment
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
                    async with seen_lock:
                        stats.geo_resolved += 1

        if not p.is_working:
            if country_filter and p.country_code != country_filter.upper():
                continue
            async with seen_lock:
                final_proxies.append(p)
            continue

        if max_latency and (p.latency if p.latency is not None else 9999) > max_latency:
            continue
        if country_filter:
            if p.country_code != country_filter.upper():
                continue

        async with seen_lock:
            final_proxies.append(p)
            stats.working += 1
            local_working_count += 1

    return local_working_count
