"""
Pipeline Stages.
Components for the streaming pipeline.
"""

import asyncio
import logging
from typing import List, Optional, Set, Dict, Union
from dataclasses import dataclass

from rich.progress import Progress, TaskID

from .models import Proxy
from .config import AppSettings
from .auto_detect import auto_detect_and_parse as parse_config
from .parsers import _extract_config_lines
from .fetcher import fetch_multiple_sources
from .async_file_ops import read_multiple_files_async
from .security_validator import validate_batch_configs, STRICT_POLICY, TEST_POLICY
from .filtering import proxy_unique_key
from .testers import SingBoxTester
from .test_cache import TestResultCache
from .scheduler import SmartRetestScheduler
from .concurrency_manager import ConcurrencyManager
from .geoip import GeoIPResolver
from .source_quality import SourceQualityTracker, calculate_diversity_score
from .anomaly import AnomalyDetector
from .performance import PerformanceTracker

if False:  # TYPE_CHECKING
    from .event_stream import EventStream

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
        self,
        success: bool,
        stats: PipelineStats,
        output_files: dict,
        error: str | None = None,
    ):
        self.success = success
        self.stats = stats
        self.output_files = output_files
        self.error = error


async def source_producer(
    sources: List[str],
    work_queue: asyncio.Queue,
    proxies: Optional[List[Proxy]],
    quality_tracker: SourceQualityTracker,
    anomaly_detector: AnomalyDetector,
    event_stream: Optional["EventStream"],
    progress: Optional[Progress],
    task_fetch: Optional[TaskID],
):
    settings = AppSettings()
    try:
        # A. Handle Pre-supplied Proxies
        if proxies:
            lines = [p.config for p in proxies if p.config]
            if lines:
                await work_queue.put(("supplied-proxies", lines))

        # B. Handle File Sources
        # Treat only real filesystem paths as local files; skip proxy URIs.
        protocol_prefixes = (
            "http://",
            "https://",
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
            "ssconf://",
        )
        local_files = [s for s in sources if not s.startswith(protocol_prefixes)]
        if local_files:
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
                await work_queue.put(("supplied-config", [s]))
            elif s.startswith("ssconf://"):
                remote_urls.append(s.replace("ssconf://", "https://"))

        active_urls = []
        blocked_urls = []
        for url in remote_urls:
            if quality_tracker.should_fetch(url):
                active_urls.append(url)
            else:
                blocked_urls.append(url)

        # If every remote source is on cooldown or disabled, surface a clear error.
        if blocked_urls and not active_urls:
            logger.error(
                "ALL %d remote sources are on cooldown/disabled - no proxies will be fetched!",
                len(blocked_urls),
            )

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
                        if count == 0:
                            logger.debug(
                                "Source %s returned content but no valid config lines",
                                source,
                            )
                            continue
                        is_safe, reason = anomaly_detector.is_safe(source, count)

                        if is_safe:
                            if lines:
                                anomaly_detector.record(source, count)
                                if event_stream:
                                    event_stream.emit(
                                        "fetch_success",
                                        f"Fetched {count} proxies from {source}",
                                    )
                                await work_queue.put((source, lines))
                        else:
                            logger.warning(f"⚠️ BLOCKING {source}: {reason}")
                            if event_stream:
                                event_stream.emit(
                                    "fetch_blocked",
                                    f"Blocked source {source}: {reason}",
                                )
    except Exception as e:
        logger.error("Producer failed: %s", e)
    finally:
        # If absolutely nothing was provided, log a clear warning – this would
        # otherwise result in a silent zero-output run.
        if not sources and not proxies:
            logger.warning(
                "No sources or pre-supplied proxies provided - pipeline will produce zero results"
            )
        await work_queue.put(None)


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
    progress: Optional[Progress],
    task_process: Optional[TaskID],
    max_proxies: Optional[int],
    max_latency: Optional[int],
    country_filter: Optional[str],
    leniency: bool,
):
    policy = TEST_POLICY if leniency else STRICT_POLICY

    # Log tester status at start for debugging
    if tester.go_tester.available:
        logger.info("Using Go batch tester for proxy testing")
    else:
        logger.warning("Go batch tester unavailable - falling back to Python tester")

    while True:
        try:
            # Add timeout to prevent indefinite blocking if producer dies
            item = await asyncio.wait_for(work_queue.get(), timeout=300.0)
        except asyncio.TimeoutError:
            logger.warning("Consumer timed out waiting for work. Exiting.")
            break

        if item is None:
            work_queue.task_done()
            break

        source, raw_lines = item
        stats.fetched_sources += 1
        stats.fetched_lines += len(raw_lines)

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

        unique_batch = []
        for p in parsed_batch:
            k = proxy_unique_key(p)
            if k not in seen_keys:
                seen_keys.add(k)
                unique_batch.append(p)

        stats.parsed += len(unique_batch)
        safe_batch = validate_batch_configs(unique_batch, policy)

        final_batch_for_this_source = []
        proxies_to_actually_test = []

        # Decide whether to reuse cached results or schedule a fresh test.
        # We treat any path that leads to an actual test as a cache miss
        # (including forced retests).
        for p in safe_batch:
            cached = None
            if not scheduler.should_retest(p):
                cached = test_cache.get(p)

            if cached:
                final_batch_for_this_source.append(cached)
            else:
                stats.cache_misses += 1
                proxies_to_actually_test.append(p)

        if proxies_to_actually_test:
            if max_proxies and stats.tested >= max_proxies:
                pass
            else:
                if tester.go_tester.available:
                    chunk_size = 50
                    for i in range(0, len(proxies_to_actually_test), chunk_size):
                        chunk = proxies_to_actually_test[i : i + chunk_size]
                        await tester.test_batch(chunk)
                        for res in chunk:
                            if res.is_working:
                                final_batch_for_this_source.append(res)
                                # Keep stats.working consistent between Go and Python paths
                                stats.working += 1
                                if event_stream:
                                    event_stream.emit(
                                        "test_success",
                                        f"Proxy working: {res.protocol}://{res.address}:{res.port} ({res.latency}ms)",
                                    )
                            else:
                                # Log test failures for debugging
                                logger.debug(
                                    f"Proxy test failed: {res.protocol}://{res.address}:{res.port}"
                                )
                        stats.tested += len(chunk)
                        # Log batch test summary
                        working_in_chunk = sum(1 for r in chunk if r.is_working)
                        logger.debug(
                            f"Batch test result: {working_in_chunk}/{len(chunk)} working"
                        )
                        if progress and task_process:
                            progress.update(
                                task_process,
                                completed=stats.tested,
                                description=f"[green]Testing... ({stats.working} working)",
                            )
                else:
                    concurrency.start_tuner()

                    async def _test_wrap(p: Proxy):
                        sem = concurrency.get_semaphore()
                        async with sem:
                            res = await tester.test(p)
                            if res.is_working:
                                if event_stream:
                                    event_stream.emit(
                                        "test_success",
                                        f"Proxy working: {res.protocol}://{res.address}:{res.port} ({res.latency}ms)",
                                    )
                            return res

                    try:
                        chunk_size = 20
                        for i in range(0, len(proxies_to_actually_test), chunk_size):
                            chunk = proxies_to_actually_test[i : i + chunk_size]
                            results = await asyncio.gather(
                                *[_test_wrap(x) for x in chunk]
                            )
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
                    finally:
                        # Always stop tuner so background task cannot leak
                        await concurrency.stop_tuner()

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
                        stats.geo_resolved += 1
            if country_filter:
                if p.country_code != country_filter.upper():
                    continue
            final_proxies.append(p)
            stats.working += 1

        working_count = sum(1 for p in final_batch_for_this_source if p.is_working)
        fetched_count = len(parsed_batch)
        diversity_score = calculate_diversity_score(final_batch_for_this_source)

        if not source.startswith("supplied-proxies") and not source.startswith(
            "sources/"
        ):
            quality_tracker.update(
                source, fetched_count, working_count, diversity_score
            )

        work_queue.task_done()

    # Log final summary with breakdown
    if stats.tested > 0 and stats.working == 0:
        logger.error(
            f"CRITICAL: All {stats.tested} proxy tests failed! "
            f"This likely indicates: 1) Go tester not available, "
            f"2) Network connectivity issues to test URLs, or "
            f"3) All proxy configurations are invalid/incompatible."
        )
    elif stats.tested > 0:
        success_rate = (stats.working / stats.tested) * 100
        logger.info(
            f"Test summary: {stats.working}/{stats.tested} working ({success_rate:.1f}% success rate)"
        )
