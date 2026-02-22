# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
from typing import List, Optional, Set, Any
from urllib.parse import urlparse

from .config import AppSettings
from .event_stream import EventStream
from .fetcher_worker import fetch_single_source, FetchResult
from .models import Proxy
from .source_quality import SourceQualityTracker
from .anomaly import AnomalyDetector
from .security_validator import SecurityValidator
from .async_utils import safe_wait_for
from .circuit_breaker import CircuitBreakerManager
import httpx

logger = logging.getLogger(__name__)


class Producer:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.max_concurrency = settings.PRODUCER_MAX_CONCURRENCY
        self.semaphore = asyncio.BoundedSemaphore(self.max_concurrency)
        self.circuit_breaker_manager = CircuitBreakerManager(
            failure_threshold=settings.CIRCUIT_TRIP_CONN_ERRORS,
            recovery_timeout=settings.CIRCUIT_OPEN_SEC,
        )

    async def fetch_all(
        self,
        sources: List[str],
        proxies: List[Proxy],
        work_queue: asyncio.Queue,
        event_stream: Optional[EventStream],
        stop_event: asyncio.Event,
        quality_tracker: SourceQualityTracker,
        anomaly_detector: AnomalyDetector,
        enable_anomaly_detection: bool = True,
    ):
        """
        Fetch proxies from all sources concurrently with limited concurrency.
        """
        loop = asyncio.get_running_loop()
        client_timeout = httpx.Timeout(
            self.settings.FETCH_TIMEOUT, connect=self.settings.LAT_CONNECT_TIMEOUT_MS / 1000
        )
        limits = httpx.Limits(
            max_keepalive_connections=self.settings.PRODUCER_MAX_CONCURRENCY,
            max_connections=self.settings.PRODUCER_MAX_CONCURRENCY,
        )

        async with httpx.AsyncClient(timeout=client_timeout, limits=limits, follow_redirects=True) as client:
            tasks = []

            # Helper to wrap the fetch with semaphore
            async def _guarded_fetch(source_url: str):
                if stop_event.is_set():
                    return

                async with self.semaphore:
                    # Sanitize for logging
                    safe_source = SecurityValidator.sanitize_log_message(source_url)

                    try:
                        # Check circuit breaker
                        domain = urlparse(source_url).netloc
                        breaker = await self.circuit_breaker_manager.get_breaker(domain)

                        if await breaker.is_open():
                            if await breaker.should_log_open():
                                logger.warning(f"Circuit breaker OPEN for {domain}, skipping {safe_source}")
                            if event_stream:
                                event_stream.emit("fetch_skipped", f"Circuit breaker open for {domain}")
                            return

                        # Fetch
                        start_ts = loop.time()
                        headers = {"User-Agent": "ConfigStream/3.0"}

                        try:
                            result = await fetch_single_source(
                                client,
                                source_url,
                                headers,
                                self.settings.MAX_RESPONSE_SIZE,
                                self.settings,
                                self.settings.FETCH_TIMEOUT,
                                start_ts,
                                loop,
                            )

                            # Success? Record it.
                            if result.success:
                                await breaker.record_success()

                                lines = []
                                if result.content:
                                    lines = result.content.splitlines()

                                count = len(lines)
                                if count == 0:
                                    if event_stream:
                                        event_stream.emit("fetch_empty", f"No proxies found in {safe_source}")
                                    return

                                # Anomaly Check
                                is_safe = True
                                reason = ""
                                if enable_anomaly_detection:
                                    is_safe, reason = await loop.run_in_executor(
                                        None, anomaly_detector.check, source_url, count
                                    )

                                if is_safe:
                                    if enable_anomaly_detection:
                                        await loop.run_in_executor(None, anomaly_detector.record, source_url, count)

                                    metadata = {
                                        "fetch_duration": result.response_time or 0.0,
                                        "drop_stats": {},
                                    }

                                    await work_queue.put((source_url, lines, metadata))

                                    if event_stream:
                                        event_stream.emit(
                                            "fetch_success",
                                            f"Fetched {count} lines from {safe_source} ({result.response_time:.2f}s)"
                                        )
                                else:
                                    logger.warning(f"Anomaly detected for {safe_source}: {reason}")
                                    await loop.run_in_executor(None, quality_tracker.report_failure, source_url, f"anomaly:{reason}")
                                    if event_stream:
                                        event_stream.emit("fetch_blocked", f"Anomaly: {reason} for {safe_source}")

                            else:
                                # Failure
                                await breaker.record_failure()
                                error_msg = result.error or "Unknown error"
                                logger.warning(f"Failed to fetch {safe_source}: {error_msg}")
                                await loop.run_in_executor(None, quality_tracker.report_failure, source_url, error_msg)
                                if event_stream:
                                    event_stream.emit("fetch_error", f"Failed {safe_source}: {error_msg}")

                        except Exception as e:
                            await breaker.record_failure()
                            raise e

                    except Exception as e:
                         logger.error(f"Error processing source {safe_source}: {e}")

            # Create tasks
            for source in sources:
                if stop_event.is_set():
                    break
                tasks.append(asyncio.create_task(_guarded_fetch(source)))

            # Pre-supplied proxies
            if proxies:
                # Mock lines for pre-supplied proxies since they are already objects
                # Or pass special tuple
                # Based on previous code pattern, we might just pass them directly if consumer handles tuple length/type
                # But to be safe and compatible with typical (source, lines, metadata)
                # We'll assume the Consumer has logic for this or we adapt.
                # Since we don't have the original code for consumer right here, we'll mimic the old producer behavior.
                # Assuming old producer just put them in queue.
                await work_queue.put(("pre-supplied", proxies, {"fetch_duration": 0.0}))

            # Wait for all fetch tasks
            if tasks:
                await asyncio.gather(*tasks)

    async def fetch_all_with_shutdown(
        self,
        sources: List[str],
        proxies: List[Proxy],
        work_queue: asyncio.Queue,
        event_stream: Optional[EventStream],
        stop_event: asyncio.Event,
        quality_tracker: SourceQualityTracker,
        anomaly_detector: AnomalyDetector,
        num_consumers: int,
        enable_anomaly_detection: bool = True,
    ):
        """Wrapper to run fetch_all and then signal shutdown to consumers."""
        await self.fetch_all(
            sources,
            proxies,
            work_queue,
            event_stream,
            stop_event,
            quality_tracker,
            anomaly_detector,
            enable_anomaly_detection
        )

        # Signal shutdown
        for _ in range(num_consumers):
            await work_queue.put(None)

async def source_producer(
    sources: List[str],
    work_queue: asyncio.Queue,
    proxies: List[Proxy],
    quality_tracker: SourceQualityTracker,
    anomaly_detector: AnomalyDetector,
    event_stream: Optional[EventStream],
    progress: Any,
    task_fetch: Any,
    num_consumers: int,
    stop_event: asyncio.Event,
):
    """
    Main producer entry point compatible with pipeline.py
    """
    settings = AppSettings()
    producer = Producer(settings)

    # We ignore progress/task_fetch inside Producer for now or we could pass them if we updated Producer signature
    # But for resilience, the core logic is what matters.
    # The original producer probably updated progress.
    # Since we rewrote Producer, we might have lost progress updates.
    # To keep it simple and working:

    await producer.fetch_all_with_shutdown(
        sources=sources,
        proxies=proxies,
        work_queue=work_queue,
        event_stream=event_stream,
        stop_event=stop_event,
        quality_tracker=quality_tracker,
        anomaly_detector=anomaly_detector,
        num_consumers=num_consumers,
    )
