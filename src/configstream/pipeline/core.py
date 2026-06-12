# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import multiprocessing
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Any
from contextlib import suppress

from .interfaces import IPipeline
from .models import PipelineContext
from configstream.pipeline_stats import PipelineStats, PipelineResult
from configstream.config import AppSettings

# Intelligence and Domain Dependencies
from configstream.testers import SingBoxTester
from configstream.test_cache import TestResultCache
from configstream.scheduler import SmartRetestScheduler
from configstream.concurrency_manager import ConcurrencyManager
from configstream.geoip import GeoIPResolver
from configstream.source_quality import SourceQualityTracker
from configstream.anomaly import AnomalyDetector
from configstream.security.blocklist import DEFAULT_BLOCKLIST
from configstream.performance import PerformanceTracker
from configstream.history.tracker import ProxyHistoryTracker
from configstream.event_stream import EventStream
from configstream.intelligence.washer.core import ProxyWasher
from configstream.utils.bloom import BloomFilter
from configstream.hard_stop import HardStopWatcher
from configstream.logging_config import set_trace_id
from configstream.async_utils import safe_wait_for
from configstream.adaptive_workers import calculate_optimal_workers

logger = logging.getLogger(__name__)


async def _cancel_all(
    producer_task: asyncio.Task, consumer_tasks: List[asyncio.Task]
) -> None:
    for t in consumer_tasks:
        t.cancel()
    producer_task.cancel()
    await asyncio.gather(*consumer_tasks, return_exceptions=True)
    try:
        await producer_task
    except asyncio.CancelledError:
        pass
    except BaseException as e:
        logger.debug(f"Producer task ended with exception during cancellation: {e}")


class StandardPipeline(IPipeline):
    def __init__(
        self,
        sources: List[str],
        producer_factory: Any,
        consumer_factory: Any,
        context: PipelineContext,
        num_consumers: int = 4,
        time_limit_seconds: Optional[int] = None,
    ):
        self.sources = sources
        self.producer_factory = producer_factory
        self.consumer_factory = consumer_factory
        self.context = context
        self.num_consumers = num_consumers
        self.context.num_consumers = num_consumers
        self.time_limit_seconds = time_limit_seconds

    @classmethod
    async def create_and_init(
        cls,
        sources: List[str],
        output_dir: str,
        producer_factory: Any,
        consumer_factory: Any,
        max_workers: int = 0,
        timeout: int = 10,
        country_filter: Optional[str] = None,
        max_latency: Optional[int] = None,
        leniency: bool = False,
        strict_security: bool = False,
        progress: Optional[Any] = None,
        dry_run: bool = False,
        time_limit_seconds: Optional[int] = None,
    ) -> "StandardPipeline":
        settings = AppSettings()
        settings.validate_settings()
        if max_workers <= 0 and settings.MAX_WORKERS > 0:
            max_workers = settings.MAX_WORKERS

        if max_workers <= 0:
            max_workers = calculate_optimal_workers(0)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        from configstream.tools.vwarp.manager import VwarpTool

        vwarp_tool = VwarpTool()

        if settings.USE_VWARP_TUNNEL:
            if await vwarp_tool.is_available():
                vwarp_config_override = {
                    "masque": {"enabled": settings.VWARP_MASQUE_ENABLED},
                    "psiphon": {
                        "enabled": settings.PSIPHON_ENABLED,
                        "country": settings.PSIPHON_COUNTRY,
                    },
                }
                from configstream.constants import VWARP_BIND_ADDRESS, VWARP_SOCKS5_PORT

                if await vwarp_tool.start_tunnel(
                    bind_addr=VWARP_BIND_ADDRESS,
                    port=VWARP_SOCKS5_PORT,
                    config_override=vwarp_config_override,
                ):
                    logger.info("✅ Vwarp Tunnel established.")
                    os.environ["USE_VWARP_TUNNEL"] = "true"
                else:
                    logger.warning(
                        "Vwarp tunnel failed to start. Disabling Vwarp integration."
                    )
                    os.environ["USE_VWARP_TUNNEL"] = "false"
            else:
                logger.warning(
                    "Vwarp tunnel requested but vwarp binary is unavailable. Disabling Vwarp integration."
                )
                os.environ["USE_VWARP_TUNNEL"] = "false"
        else:
            logger.info("Vwarp tunnel disabled by configuration.")

        test_cache = TestResultCache()
        scheduler = SmartRetestScheduler(cache=test_cache)
        concurrency = ConcurrencyManager(
            asyncio.get_running_loop(),
            initial_limit=max_workers,
            min_limit=1,
            max_limit=max_workers,
        )

        logger.info("Initializing security blocklists...")
        await DEFAULT_BLOCKLIST.update()

        geoip = GeoIPResolver()
        washer = ProxyWasher(settings.WARP_KEY_POOL)
        if not dry_run:
            await washer.fetch_clean_ips()

        event_stream = EventStream(output_path)
        trace_id = set_trace_id()
        stats = PipelineStats()
        stats.trace_id = trace_id
        stats.total_configured_sources = len(sources) if sources else 0

        tester = SingBoxTester(
            timeout=float(timeout),
            cache=test_cache,
            strict_security=strict_security,
            dry_run=dry_run,
            max_workers=max_workers,
        )

        seen_bloom = None
        if settings.SEEN_BLOOM_ENABLED:
            seen_bloom = BloomFilter(
                expected_items=int(settings.SEEN_BLOOM_EXPECTED_ITEMS),
                false_positive_rate=float(settings.SEEN_BLOOM_FALSE_POSITIVE_RATE),
            )

        context = PipelineContext(
            work_queue=asyncio.Queue(maxsize=5000),
            stop_event=asyncio.Event(),
            stats=stats,
            final_proxies=[],
            seen_keys={},
            seen_lock=asyncio.Lock(),
            settings=settings,
            tester=tester,
            scheduler=scheduler,
            test_cache=test_cache,
            concurrency=concurrency,
            geoip=geoip,
            tracker=PerformanceTracker(),
            event_stream=event_stream,
            quality_tracker=SourceQualityTracker(),
            history=ProxyHistoryTracker(),
            anomaly_detector=AnomalyDetector(),
            washer=washer,
            seen_bloom=seen_bloom,
            hard_stop_watcher=HardStopWatcher(
                grace_seconds=float(getattr(settings, "SHUTDOWN_GRACE_SECONDS", 5.0)),
                flush_timeout_seconds=float(
                    getattr(settings, "EVENT_STREAM_FLUSH_TIMEOUT_SECONDS", 2.0)
                ),
            ),
            progress=progress,
            max_latency=max_latency,
            country_filter=country_filter,
            leniency=leniency,
            strict_security=strict_security,
            dry_run=dry_run,
        )

        cpu_count = multiprocessing.cpu_count()
        optimal_consumers = max(4, min(int(cpu_count * 1.5), 32))
        if max_workers > 200:
            optimal_consumers = max(optimal_consumers, 16)

        return cls(
            sources=sources,
            producer_factory=producer_factory,
            consumer_factory=consumer_factory,
            context=context,
            num_consumers=optimal_consumers,
            time_limit_seconds=time_limit_seconds,
        )

    async def run(self) -> PipelineResult:
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting pipeline with {self.num_consumers} parallel consumers")

        if self.time_limit_seconds:
            self.context.stats.time_limit_seconds = self.time_limit_seconds

        if self.context.tester and self.context.tester.go_tester.available:
            try:
                await self.context.tester.go_tester.start()
            except Exception as e:
                logger.warning(
                    f"Failed to start Go tester daemon: {e}. Fallback enabled."
                )
                self.context.tester.go_tester.available = False

        if self.context.tester and not self.context.tester.go_tester.available:
            if self.context.concurrency:
                await self.context.concurrency.start_tuner()

        producer = self.producer_factory(self.sources, self.context)
        consumers = [
            self.consumer_factory(self.context, i) for i in range(self.num_consumers)
        ]

        time_limit_task: Optional[asyncio.Task] = None
        if self.time_limit_seconds and self.time_limit_seconds > 0:
            logger.info(f"Batch time limit enabled: {self.time_limit_seconds}s")

            async def _time_limit_watcher():
                await asyncio.sleep(self.time_limit_seconds)
                if not self.context.stop_event.is_set():
                    self.context.stats.time_limited = True
                    self.context.stop_event.set()
                    logger.warning("Batch time limit reached. Stopping intake.")

            time_limit_task = asyncio.create_task(_time_limit_watcher())

        producer_task = asyncio.create_task(producer.produce())
        consumer_tasks = [asyncio.create_task(c.consume()) for c in consumers]

        try:
            try:
                gather_task = asyncio.gather(producer_task, *consumer_tasks)
                if self.time_limit_seconds and self.time_limit_seconds > 0:
                    grace_seconds = int(
                        getattr(
                            self.context.settings, "BATCH_TIME_LIMIT_GRACE_SECONDS", 0
                        )
                    )
                    await safe_wait_for(
                        gather_task,
                        timeout=self.time_limit_seconds + max(0, grace_seconds),
                    )
                else:
                    await gather_task
            except asyncio.TimeoutError:
                self.context.stats.time_limited = True
                self.context.stop_event.set()
                logger.warning(
                    "Hard batch time limit reached. Cancelling pipeline tasks."
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
            stats = self.context.stats
            _zero_working = stats.tested > 0 and stats.working == 0
            if _zero_working:
                logger.warning(
                    f"All {stats.tested} proxy tests failed across all sources. "
                    "Output will still be generated with is_working=False so downstream "
                    "consumers can attempt their own connectivity checks."
                )

            from configstream.filtering import (
                dedupe_and_shuffle,
                filter_unique_endpoints,
                dedupe_by_config,
            )
            from configstream.sorter import sort_proxies_pareto
            import configstream.output_handler as output_handler

            optimized_proxies = dedupe_and_shuffle(self.context.final_proxies)
            optimized_proxies = dedupe_by_config(optimized_proxies)
            if self.context.settings.ENABLE_ENDPOINT_FILTERING:
                optimized_proxies = filter_unique_endpoints(optimized_proxies)
            else:
                logger.info("Endpoint filtering disabled by configuration.")

            if self.context.history:
                sort_proxies_pareto(optimized_proxies, self.context.history)

            stats.final_count = len(optimized_proxies)
            stats.end_time = datetime.now(timezone.utc)
            duration = (stats.end_time - start_time).total_seconds()
            stats.duration = float(duration)

            if self.context.quality_tracker:
                failing_sources = self.context.quality_tracker.get_worst_sources(
                    limit=5
                )
                if failing_sources:
                    from configstream.security_validator import SecurityValidator

                    log_lines = []
                    for s_data in failing_sources:
                        safe_url = SecurityValidator.sanitize_log_message(s_data["url"])
                        log_lines.append(
                            f"  - {safe_url}: score={s_data['score']:.1f}, reason={s_data.get('last_failure_reason', 'unknown')}"
                        )
                    logger.info("⚠️ Top 5 Failing Sources:\n" + "\n".join(log_lines))

            # Needs output_dir, which we didn't save in context, we can derive it from event stream
            output_path = Path("output")
            if self.context.event_stream and hasattr(
                self.context.event_stream, "output_dir"
            ):
                output_path = self.context.event_stream.output_dir

            history = self.context.history
            if history is None:
                raise RuntimeError(
                    "PipelineContext.history is required to generate outputs"
                )

            generated_files = await output_handler.generate_pipeline_outputs(
                optimized_proxies,
                output_path,
                stats,
                history,
                washer=self.context.washer,
                tester=self.context.tester,
            )

            if self.context.scheduler:
                sched_stats = self.context.scheduler.get_scheduling_statistics()
                if sched_stats:
                    logger.info(f"Scheduler stats: {sched_stats}")
            if self.context.anomaly_detector:
                self.context.anomaly_detector.get_statistics()

            history.save()
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None, lambda: history.cleanup_old_data(days=30)
                )
            except Exception as e:
                logger.warning(f"History cleanup failed: {e}")

            if self.context.test_cache:
                self.context.test_cache.save()

            # Server notify
            try:
                import httpx

                async with httpx.AsyncClient(timeout=1.0) as client:
                    await client.post(
                        "http://127.0.0.1:8000/api/admin/notify-update",
                        json={
                            "timestamp": (
                                stats.end_time.isoformat()
                                if stats.end_time
                                else duration
                            )
                        },
                    )
            except Exception as e:
                logger.debug(f"Server notification skipped: {e}")

            should_fail = (
                self.context.strict_security
                or bool(getattr(self.context.settings, "FAIL_ON_ZERO_WORKING", False))
            ) and bool(_zero_working) and not stats.time_limited

            if should_fail:
                logger.error(
                    "0 working proxies detected and strict mode is enabled; marking pipeline result as failed."
                )

            logger.info("Pipeline execution completed")
            return PipelineResult(
                success=not should_fail,
                stats=stats,
                output_files=generated_files,
                error="0 working proxies detected" if should_fail else None,
            )

        finally:
            if time_limit_task and not time_limit_task.done():
                time_limit_task.cancel()
                with suppress(asyncio.CancelledError):
                    await time_limit_task

            if self.context.concurrency:
                await self.context.concurrency.stop_tuner()

            if self.context.hard_stop_watcher and self.context.tester:
                await self.context.hard_stop_watcher.stop_tester(self.context.tester)

            from configstream.tools.vwarp.manager import VwarpTool

            await VwarpTool().stop_tunnel()

            if self.context.anomaly_detector:
                self.context.anomaly_detector.close()

            if self.context.hard_stop_watcher and self.context.event_stream:
                await self.context.hard_stop_watcher.flush_event_stream(
                    self.context.event_stream
                )

            from configstream.logging_config import clear_trace_id

            clear_trace_id()


async def run_full_pipeline(
    sources: List[str],
    output_dir: str,
    max_workers: int = 0,
    timeout: int = 10,
    country_filter: Optional[str] = None,
    max_latency: Optional[int] = None,
    leniency: bool = False,
    strict_security: bool = False,
    progress: Optional[Any] = None,
    dry_run: bool = False,
    time_limit_seconds: Optional[int] = None,
    proxies: Optional[List[Any]] = None,
) -> PipelineResult:
    from configstream.pipeline.producer import StreamingProducer
    from configstream.pipeline.consumer import WorkerConsumer

    pipeline = await StandardPipeline.create_and_init(
        sources=sources,
        output_dir=output_dir,
        producer_factory=StreamingProducer,
        consumer_factory=WorkerConsumer,
        max_workers=max_workers,
        timeout=timeout,
        country_filter=country_filter,
        max_latency=max_latency,
        leniency=leniency,
        strict_security=strict_security,
        progress=progress,
        dry_run=dry_run,
        time_limit_seconds=time_limit_seconds,
    )
    if proxies:
        pipeline.context.final_proxies.extend(proxies)
    return await pipeline.run()
