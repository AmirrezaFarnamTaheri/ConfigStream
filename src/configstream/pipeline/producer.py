# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import json
import random
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from rich.progress import Progress, TaskID
from functools import partial
from urllib.parse import urlparse

from configstream.models import Proxy
from configstream.config import AppSettings
from configstream.backpressure import (
    BackpressurePolicy,
    enqueue as enqueue_with_policy,
    select_candidates,
)
import configstream.producer as producer_mod
from configstream.circuit_breaker import CircuitBreakerManager
from configstream.parsers import extract_config_lines
from configstream.source_quality import SourceQualityTracker
from configstream.anomaly import AnomalyDetector
from configstream.security_validator import SecurityValidator
from configstream.pipeline.interfaces import IProducer
from configstream.pipeline.models import PipelineContext

if TYPE_CHECKING:
    from configstream.event_stream import EventStream
    from configstream.pipeline_stats import PipelineStats

logger = logging.getLogger(__name__)


class StreamingProducer(IProducer):
    def __init__(self, sources: List[str], context: PipelineContext):
        self.sources = sources
        self.context = context

    async def produce(self) -> None:
        # Contract: the pipeline core always provides these trackers.
        if (
            self.context.quality_tracker is None
            or self.context.anomaly_detector is None
        ):
            raise RuntimeError(
                "PipelineContext is missing quality_tracker/anomaly_detector; "
                "StreamingProducer requires a fully initialised context"
            )

        try:
            await source_producer(
                self.sources,
                self.context.work_queue,
                getattr(self.context, "supplied_proxies", None),
                self.context.quality_tracker,
                self.context.anomaly_detector,
                self.context.event_stream,
                self.context.progress,
                self.context.task_fetch,
                num_consumers=getattr(self.context, "num_consumers", 4),
                stop_event=self.context.stop_event,
                stats=self.context.stats,
            )
        except Exception as e:
            from configstream.security_validator import SecurityValidator

            safe_err = SecurityValidator.sanitize_log_message(str(e))
            logger.error(
                "StreamingProducer encountered an unhandled exception [%s]: %s",
                type(e).__name__,
                safe_err,
            )
            raise


def _chunk_lines(lines: List[str], chunk_size: int) -> List[List[str]]:
    """Split large source payloads into bounded chunks for fair queueing."""
    if chunk_size <= 0 or len(lines) <= chunk_size:
        return [lines]
    return [lines[i : i + chunk_size] for i in range(0, len(lines), chunk_size)]


def _chunk_metadata(
    base: Dict[str, Any], index: int, total: int, queued: int
) -> Dict[str, Any]:
    metadata = dict(base, count_source=queued == 0)
    if index > 1:
        metadata["drop_stats"] = {}
    if total > 1:
        metadata.update(chunk_index=index, chunk_total=total)
    return metadata


async def _report_source_failure(
    loop: asyncio.AbstractEventLoop,
    quality_tracker: SourceQualityTracker,
    settings: AppSettings,
    source: str,
    reason: str,
    duration_ms: float = 0.0,
    failure_modes: Optional[dict] = None,
) -> None:
    """Report a source failure to the quality tracker (best-effort)."""
    try:
        await loop.run_in_executor(None, quality_tracker.report_failure, source, reason)
        batch_number = str(getattr(settings, "BATCH_NUMBER", "")).strip()
        batch_source = f"batch_{batch_number}" if batch_number else "pipeline"
        await loop.run_in_executor(
            None,
            quality_tracker.record_run,
            source,
            {
                "timestamp": int(time.time()),
                "duration_ms": duration_ms,
                "fetched_count": 0,
                "working_count": 0,
                "geoip_json": "{}",
                "failure_modes_json": json.dumps(failure_modes or {}),
                "batch_source": batch_source,
            },
        )
    except Exception:  # nosec B110
        logging.getLogger(__name__).debug("Suppressed broad exception")
        pass


async def _report_source_backpressure(
    loop: asyncio.AbstractEventLoop,
    quality_tracker: SourceQualityTracker,
    settings: AppSettings,
    source: str,
    dropped: int,
    duration_ms: float = 0.0,
) -> None:
    """Record queue pressure without penalizing the source health score."""
    try:
        batch_number = str(getattr(settings, "BATCH_NUMBER", "")).strip()
        batch_source = f"batch_{batch_number}" if batch_number else "pipeline"
        await loop.run_in_executor(
            None,
            quality_tracker.record_run,
            source,
            {
                "timestamp": int(time.time()),
                "duration_ms": duration_ms,
                "fetched_count": 0,
                "working_count": 0,
                "geoip_json": "{}",
                "failure_modes_json": json.dumps({"backpressure_drop": dropped}),
                "batch_source": batch_source,
            },
        )
    except Exception:  # nosec B110
        logging.getLogger(__name__).debug("Suppressed broad exception")
        pass


async def source_producer(
    sources: List[str],
    work_queue: asyncio.Queue,
    proxies: Optional[List[Proxy]],
    quality_tracker: SourceQualityTracker,
    anomaly_detector: AnomalyDetector,
    event_stream: Optional["EventStream"],
    progress: Optional[Progress],
    task_fetch: Optional[TaskID],
    num_consumers: int = 1,
    stop_event: Optional[asyncio.Event] = None,
    stats: Optional["PipelineStats"] = None,
):
    settings = AppSettings()
    if stop_event is None:
        stop_event = asyncio.Event()
    enable_anomaly_detection = settings.ENABLE_ANOMALY_DETECTION
    loop = asyncio.get_running_loop()
    queue_policy = BackpressurePolicy(
        mode=str(getattr(settings, "QUEUE_DEGRADATION_MODE", "lossless")),
        put_timeout_seconds=max(
            0.05, float(getattr(settings, "QUEUE_PUT_TIMEOUT_SECONDS", 0.75))
        ),
        overload_threshold=float(getattr(settings, "QUEUE_OVERLOAD_THRESHOLD", 0.8)),
        keep_ratio=float(getattr(settings, "QUEUE_OVERLOAD_KEEP_RATIO", 0.6)),
        max_tries=max(1, int(getattr(settings, "QUEUE_MAX_TRIES", 5))),
    )
    ingest_chunk_size = max(1, int(getattr(settings, "INGEST_MICRO_CHUNK_LINES", 500)))
    breaker_manager = CircuitBreakerManager(
        failure_threshold=max(1, int(getattr(settings, "CIRCUIT_TRIP_CONN_ERRORS", 5))),
        recovery_timeout=max(1, int(getattr(settings, "CIRCUIT_OPEN_SEC", 120))),
    )

    def _queue_pressure() -> float:
        maxsize = getattr(work_queue, "maxsize", 0) or 0
        if maxsize <= 0:
            return 0.0
        return float(work_queue.qsize()) / float(maxsize)

    def _record_backpressure_drop(
        source: str, metadata: Dict[str, Any], dropped: int
    ) -> None:
        if dropped <= 0:
            return
        drop_stats = metadata.setdefault("drop_stats", {})
        if isinstance(drop_stats, dict):
            drop_stats["backpressure_drop"] = (
                int(drop_stats.get("backpressure_drop", 0)) + dropped
            )
        if stats is not None:
            stats.record_backpressure_drop(dropped)
        safe_source = SecurityValidator.sanitize_log_message(source)
        logger.warning(
            "Backpressure drop: source=%s dropped=%d pressure=%.2f",
            safe_source,
            dropped,
            _queue_pressure(),
        )

    async def _queue_payload(
        source: str, lines: List[str], metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Enqueue payload with micro-chunking and bounded put timeout.
        Returns number of chunks successfully queued.
        """
        base_meta: Dict[str, Any] = dict(metadata or {})
        chunks = _chunk_lines(lines, ingest_chunk_size)
        queued_chunks = 0

        for idx, chunk in enumerate(chunks, start=1):
            chunk_meta = _chunk_metadata(base_meta, idx, len(chunks), queued_chunks)

            candidate_lines, dropped = select_candidates(
                chunk, pressure=_queue_pressure(), policy=queue_policy
            )
            if dropped:
                _record_backpressure_drop(source, chunk_meta, dropped)
            if not candidate_lines:
                continue

            result = await enqueue_with_policy(
                work_queue,
                (source, candidate_lines, chunk_meta),
                policy=queue_policy,
                stop_event=stop_event,
            )
            if result.enqueued:
                queued_chunks += 1
                if result.attempts > 1:
                    logger.info(
                        "Queue capacity recovered after %d attempts; lossless payload retained",
                        result.attempts,
                    )
                continue
            if result.dropped:
                _record_backpressure_drop(source, chunk_meta, len(candidate_lines))
                safe_source = SecurityValidator.sanitize_log_message(source)
                logger.warning(
                    "Explicit shed-longest policy dropped chunk from %s "
                    "(size=%d, attempts=%d, pressure=%.2f)",
                    safe_source,
                    len(candidate_lines),
                    result.attempts,
                    _queue_pressure(),
                )
                if event_stream:
                    event_stream.emit(
                        "warning",
                        f"Explicit overload policy dropped {len(candidate_lines)} lines "
                        f"from {safe_source}",
                    )
            if result.stopped:
                break

        return queued_chunks

    def _is_direct_proxy(candidate: str) -> bool:
        lower = candidate.lower()
        if lower.startswith(
            (
                "ss://",
                "vmess://",
                "vless://",
                "trojan://",
                "hysteria://",
                "hy2://",
                "hysteria2://",
                "hy3://",
                "hysteria3://",
                "tuic://",
                "ssh://",
                "wg://",
                "wireguard://",
                "naive://",
                "naive+https://",
                "naive+http://",
                "socks://",
                "socks4://",
                "socks5://",
            )
        ):
            return True
        if lower.startswith(("http://", "https://")):
            parsed = urlparse(candidate)
            return (
                parsed.hostname is not None
                and parsed.port is not None
                and parsed.path in ("", "/")
                and not parsed.query
                and not parsed.fragment
            )
        return False

    # Set when this coroutine is cancelled, so the sentinel-delivery loop in the
    # finally block can tell a forced teardown from a normal completion.
    producer_cancelled = False

    try:
        # A. Handle Pre-supplied Proxies
        if proxies:
            supplied_lines = [p.config for p in proxies if p.config]
            if supplied_lines:
                await _queue_payload("supplied-proxies", supplied_lines, {})

        # B. Handle File Sources
        local_files: List[str] = []
        remote_urls: List[str] = []
        for raw in sources:
            if stop_event.is_set():
                break
            s = raw.strip()
            if not s:
                continue
            lower = s.lower()
            if _is_direct_proxy(s):
                await _queue_payload("supplied-config", [s], {})
            elif lower.startswith("ssconf://"):
                remote_urls.append(s.replace("ssconf://", "https://", 1))
            elif lower.startswith(("http://", "https://")):
                remote_urls.append(s)
            else:
                local_files.append(s)

        if local_files:
            file_results = await producer_mod.read_multiple_files_async(local_files)
            for fpath, content in file_results:
                if stop_event.is_set():
                    break
                extract_func = partial(extract_config_lines, content, source_url=fpath)
                (
                    file_lines,
                    drop_stats,
                ) = await asyncio.get_running_loop().run_in_executor(None, extract_func)
                if file_lines:
                    metadata: dict[str, object] = {"drop_stats": drop_stats}
                    queued = await _queue_payload(fpath, file_lines, metadata)
                    if queued == 0:
                        await _report_source_backpressure(
                            loop,
                            quality_tracker,
                            settings,
                            fpath,
                            len(file_lines),
                        )
                else:
                    await _report_source_failure(
                        loop,
                        quality_tracker,
                        settings,
                        fpath,
                        "no_valid_lines",
                        failure_modes=drop_stats,
                    )
                if progress and task_fetch:
                    progress.advance(task_fetch)

        # C. Handle Remote Sources
        active_urls = []
        blocked_urls = []

        # Use dynamic semaphore limit from settings
        sem_limit = getattr(settings, "PRODUCER_MAX_CONCURRENCY", 100)
        sem_limit = max(1, int(sem_limit))
        sem = asyncio.Semaphore(sem_limit)

        async def _check_url(url):
            async with sem:
                should_fetch = await loop.run_in_executor(
                    None, quality_tracker.should_fetch, url
                )
                return url, should_fetch

        # Process in chunks to avoid creating too many tasks at once
        chunk_size = 500
        for i in range(0, len(remote_urls), chunk_size):
            chunk = remote_urls[i : i + chunk_size]
            tasks = [_check_url(url) for url in chunk]
            check_results = await asyncio.gather(*tasks)

            for url, should_fetch in check_results:
                if should_fetch:
                    active_urls.append(url)
                else:
                    blocked_urls.append(url)

        # If every remote source is on cooldown or disabled, surface a clear error.
        if blocked_urls and not active_urls:
            logger.error(
                "ALL %d remote sources are on cooldown/disabled - no proxies will be fetched!",
                len(blocked_urls),
            )
            # Log all blocked sources in one summary to avoid spam
            blocked_count = len(blocked_urls)
            logger.info(
                f"{blocked_count} source(s) were skipped due to cooldown/disabled status."
            )
            logger.debug(
                "Blocked sources: %s",
                [SecurityValidator.sanitize_log_message(u) for u in blocked_urls],
            )

        if active_urls and not stop_event.is_set():
            logger.info(
                f"Starting fetch for {len(active_urls)} active sources "
                f"(Batch Size: 100, Concurrent Limit: {settings.PER_HOST_MAX_CONCURRENCY})"
            )
            batch_size = 100  # Increased from 50 to 100 for better throughput
            for i in range(0, len(active_urls), batch_size):
                if stop_event.is_set():
                    break
                # Add jitter to prevent overwhelming remote servers or rate limits
                if i > 0:
                    jitter = random.uniform(0.5, 2.0)  # nosec B311
                    logger.debug(f"Batch jitter: sleeping {jitter:.2f}s")
                    await asyncio.sleep(jitter)

                batch = active_urls[i : i + batch_size]
                logger.info(
                    f"Fetching batch {i // batch_size + 1}: {len(batch)} sources"
                )
                results = await producer_mod.fetch_multiple_sources(
                    batch,
                    max_concurrent=settings.PER_HOST_MAX_CONCURRENCY,
                    timeout=settings.FETCH_TIMEOUT,
                    use_adaptive_timeout=True,
                    quality_tracker=quality_tracker,
                    breaker_manager=breaker_manager,
                )

                for source, res in results.items():
                    if stop_event.is_set():
                        break
                    if res.success:
                        # Offload parsing to executor and handle stats
                        # Use partial to pass keyword argument to run_in_executor
                        extract_func = partial(
                            extract_config_lines, res.content, source_url=source
                        )
                        lines, drop_stats = await loop.run_in_executor(
                            None, extract_func
                        )

                        count = len(lines)
                        safe_source = SecurityValidator.sanitize_log_message(source)

                        if count == 0:
                            # Log that we got content but no proxies (useful for debugging invalid formats)
                            # Reduced noise for expected empty sources
                            log_method = (
                                logger.debug
                                if len(res.content) < 100
                                else logger.warning
                            )
                            log_method(
                                f"Source {safe_source} returned content (size={len(res.content) if res.content else 0}) but no valid config lines found. "
                                f"Drop Stats: {drop_stats}"
                            )
                            await _report_source_failure(
                                loop,
                                quality_tracker,
                                settings,
                                source,
                                "no_valid_lines",
                                duration_ms=(res.response_time or 0.0) * 1000,
                                failure_modes=drop_stats,
                            )
                            continue

                        # Offload anomaly check to executor to avoid blocking on DB/ML
                        if enable_anomaly_detection:
                            try:
                                is_safe, reason = await loop.run_in_executor(
                                    None, anomaly_detector.is_safe, source, count
                                )
                            except Exception as ad_err:
                                safe_err = SecurityValidator.sanitize_log_message(
                                    str(ad_err)
                                )
                                logger.warning(
                                    f"Anomaly check failed for {safe_source} ({safe_err}); failing open"
                                )
                                is_safe, reason = (
                                    True,
                                    f"Anomaly detector error (Fail Open): {safe_err}",
                                )
                        else:
                            is_safe, reason = True, "Anomaly detection disabled"

                        if is_safe:
                            if lines:
                                logger.debug(
                                    f"Anomaly check passed for {safe_source} (Count: {count})"
                                )
                                # Offload record to executor
                                if enable_anomaly_detection:
                                    try:
                                        await loop.run_in_executor(
                                            None, anomaly_detector.record, source, count
                                        )
                                    except Exception as rec_err:
                                        safe_rec_err = (
                                            SecurityValidator.sanitize_log_message(
                                                str(rec_err)
                                            )
                                        )
                                        logger.debug(
                                            f"Anomaly record failed for {safe_source}: {safe_rec_err}"
                                        )
                                # Prepare metadata and fetch time
                                resp_time = getattr(res, "response_time", None)
                                fetch_time = (
                                    f"{resp_time:.2f}s"
                                    if resp_time is not None
                                    else "N/A"
                                )
                                metadata = {
                                    "fetch_duration": resp_time or 0.0,
                                    "drop_stats": drop_stats,  # Pass stats downstream
                                }
                                queued = await _queue_payload(source, lines, metadata)
                                if queued == 0:
                                    await _report_source_backpressure(
                                        loop,
                                        quality_tracker,
                                        settings,
                                        source,
                                        len(lines),
                                        duration_ms=(res.response_time or 0.0) * 1000,
                                    )
                                    continue

                                # Single consolidated log via event stream (includes fetch metrics)
                                if event_stream:
                                    event_stream.emit(
                                        "fetch_success",
                                        f"Fetched {count} proxies from {safe_source} (Fetch: {fetch_time})",
                                    )
                        else:
                            logger.warning(
                                f"⚠️ BLOCKING {safe_source}: {reason} (count={count})"
                            )
                            try:
                                await loop.run_in_executor(
                                    None,
                                    quality_tracker.report_failure,
                                    source,
                                    f"anomaly_blocked:{reason}",
                                )
                            except Exception:  # nosec B110
                                logging.getLogger(__name__).debug(
                                    "Suppressed broad exception"
                                )
                                pass
                            if event_stream:
                                event_stream.emit(
                                    "fetch_blocked",
                                    f"Blocked source {safe_source}: {reason}",
                                )
                    else:
                        safe_source = SecurityValidator.sanitize_log_message(source)
                        safe_error = (
                            SecurityValidator.sanitize_log_message(str(res.error))
                            if res.error
                            else "unknown"
                        )
                        logger.warning(
                            f"Failed to fetch {safe_source}: {safe_error} "
                            f"(Status: {res.status_code})"
                        )
                        await _report_source_failure(
                            loop,
                            quality_tracker,
                            settings,
                            source,
                            safe_error,
                            duration_ms=(res.response_time or 0.0) * 1000,
                            failure_modes={"fetch_error": safe_error},
                        )
    except asyncio.CancelledError:
        # Cancellation is the one signal that consumers are being torn down
        # directly (core.py's `_cancel_all` cancels producer and consumers
        # together). The sentinel loop below uses this to avoid blocking on a
        # queue nobody will drain again. Note `stop_event` alone is NOT that
        # signal: the batch time-limit watcher sets it to stop intake while
        # consumers keep running and draining normally.
        producer_cancelled = True
        raise
    except Exception as e:
        safe_error = SecurityValidator.sanitize_log_message(str(e))
        logger.error(f"Producer failed: {safe_error}")
        raise
    finally:
        # If absolutely nothing was provided, log a clear warning – this would
        # otherwise result in a silent zero-output run.
        if not sources and not proxies:
            logger.warning(
                "No sources or pre-supplied proxies provided - pipeline will produce zero results"
            )

        # Signal all consumers to exit. Every consumer only terminates on this
        # None sentinel and otherwise awaits work_queue.get() forever, and the
        # pipeline awaits every consumer task -- so in the normal (healthy)
        # completion path we must NOT give up early: consumers are alive and
        # draining, so a transiently full queue always clears given patience,
        # and abandoning a sentinel would strand that consumer permanently.
        #
        # When this producer is *cancelled*, core.py's `_cancel_all` is tearing
        # the pipeline down and has cancelled every consumer too -- so the queue
        # may stay full forever with nobody left to drain it. Sentinel delivery
        # is then redundant (consumers exit via cancel(), not via this marker)
        # and must not block, or this finally would wedge the whole shutdown.
        loop = asyncio.get_running_loop()
        sentinel_deadline = loop.time() + max(
            5.0, float(settings.SHUTDOWN_GRACE_SECONDS)
        )
        for _ in range(num_consumers):
            while True:
                try:
                    work_queue.put_nowait(None)
                    break
                except asyncio.QueueFull:
                    if producer_cancelled:
                        logger.warning(
                            "Skipping sentinel delivery during forced teardown; "
                            "consumers are being cancelled directly."
                        )
                        break
                    try:
                        await asyncio.wait_for(work_queue.put(None), timeout=5.0)
                        break
                    except asyncio.TimeoutError:
                        if loop.time() >= sentinel_deadline:
                            logger.error(
                                "Sentinel delivery deadline exceeded; abandoning "
                                "remaining marker after consumer failure or stall."
                            )
                            break
                        logger.debug(
                            "Sentinel enqueue still blocked after 5s; retrying "
                            "within the bounded shutdown deadline."
                        )
                        continue
