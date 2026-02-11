# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import logging
import json
import os
import random
import time
from typing import List, Optional, TYPE_CHECKING
from rich.progress import Progress, TaskID
from functools import partial
from urllib.parse import urlparse

from configstream.models import Proxy
from configstream.config import AppSettings
from configstream.fetcher import fetch_multiple_sources
from configstream.async_file_ops import read_multiple_files_async
from configstream.parsers import _extract_config_lines
from configstream.source_quality import SourceQualityTracker
from configstream.anomaly import AnomalyDetector
from configstream.security_validator import SecurityValidator

if TYPE_CHECKING:
    from configstream.event_stream import EventStream

logger = logging.getLogger(__name__)


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
):
    settings = AppSettings()
    if stop_event is None:
        stop_event = asyncio.Event()
    enable_anomaly_detection = settings.ENABLE_ANOMALY_DETECTION
    loop = asyncio.get_running_loop()

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

    try:
        # A. Handle Pre-supplied Proxies
        if proxies:
            supplied_lines = [p.config for p in proxies if p.config]
            if supplied_lines:
                await work_queue.put(("supplied-proxies", supplied_lines, {}))

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
                await work_queue.put(("supplied-config", [s], {}))
            elif lower.startswith("ssconf://"):
                remote_urls.append(s.replace("ssconf://", "https://", 1))
            elif lower.startswith(("http://", "https://")):
                remote_urls.append(s)
            else:
                local_files.append(s)

        if local_files:
            file_results = await read_multiple_files_async(local_files)
            for fpath, content in file_results:
                if stop_event.is_set():
                    break
                extract_func = partial(_extract_config_lines, content, source_url=fpath)
                file_lines, drop_stats = (
                    await asyncio.get_running_loop().run_in_executor(None, extract_func)
                )
                if file_lines:
                    metadata: dict[str, object] = {"drop_stats": drop_stats}
                    await work_queue.put((fpath, file_lines, metadata))
                else:
                    try:
                        await loop.run_in_executor(
                            None,
                            quality_tracker.report_failure,
                            fpath,
                            "no_valid_lines",
                        )
                        batch_number = os.getenv("BATCH_NUMBER", "").strip()
                        batch_source = (
                            f"batch_{batch_number}" if batch_number else "pipeline"
                        )
                        await loop.run_in_executor(
                            None,
                            quality_tracker.record_run,
                            fpath,
                            {
                                "timestamp": int(time.time()),
                                "duration_ms": 0.0,
                                "fetched_count": 0,
                                "working_count": 0,
                                "geoip_json": "{}",
                                "failure_modes_json": json.dumps(drop_stats or {}),
                                "batch_source": batch_source,
                            },
                        )
                    except Exception:
                        pass
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
                    jitter = random.uniform(0.5, 2.0)
                    logger.debug(f"Batch jitter: sleeping {jitter:.2f}s")
                    await asyncio.sleep(jitter)

                batch = active_urls[i : i + batch_size]
                logger.info(
                    f"Fetching batch {i // batch_size + 1}: {len(batch)} sources"
                )
                results = await fetch_multiple_sources(
                    batch,
                    max_concurrent=settings.PER_HOST_MAX_CONCURRENCY,
                    timeout=settings.FETCH_TIMEOUT,
                    use_adaptive_timeout=True,
                    quality_tracker=quality_tracker,
                )

                for source, res in results.items():
                    if stop_event.is_set():
                        break
                    if res.success:
                        # Offload parsing to executor and handle stats
                        # [FIX] Use partial to pass keyword argument to run_in_executor
                        extract_func = partial(
                            _extract_config_lines, res.content, source_url=source
                        )
                        lines, drop_stats = await loop.run_in_executor(
                            None, extract_func
                        )

                        count = len(lines)
                        safe_source = SecurityValidator.sanitize_log_message(source)

                        if count == 0:
                            # Log that we got content but no proxies (useful for debugging invalid formats)
                            # Fix logging format error (don't mix % formatting with f-strings/args)
                            # Reduced noise for expected empty sources
                            log_method = (
                                logger.debug
                                if len(res.content) < 100
                                else logger.warning
                            )
                            log_method(
                                "Source %s returned content (size=%d) but no valid config lines found. "
                                "Drop Stats: %s",
                                safe_source,
                                len(res.content) if res.content else 0,
                                drop_stats,
                            )
                            try:
                                await loop.run_in_executor(
                                    None,
                                    quality_tracker.report_failure,
                                    source,
                                    "no_valid_lines",
                                )
                                batch_number = os.getenv("BATCH_NUMBER", "").strip()
                                batch_source = (
                                    f"batch_{batch_number}"
                                    if batch_number
                                    else "pipeline"
                                )
                                await loop.run_in_executor(
                                    None,
                                    quality_tracker.record_run,
                                    source,
                                    {
                                        "timestamp": int(time.time()),
                                        "duration_ms": (
                                            (res.response_time or 0.0) * 1000
                                        ),
                                        "fetched_count": 0,
                                        "working_count": 0,
                                        "geoip_json": "{}",
                                        "failure_modes_json": json.dumps(
                                            drop_stats or {}
                                        ),
                                        "batch_source": batch_source,
                                    },
                                )
                            except Exception:
                                pass
                            continue

                        # Offload anomaly check to executor to avoid blocking on DB/ML
                        if enable_anomaly_detection:
                            is_safe, reason = await loop.run_in_executor(
                                None, anomaly_detector.is_safe, source, count
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
                                    await loop.run_in_executor(
                                        None, anomaly_detector.record, source, count
                                    )
                                # Prepare metadata and fetch time
                                fetch_time = (
                                    f"{res.response_time:.2f}s"
                                    if res.response_time is not None
                                    else "N/A"
                                )
                                metadata = {
                                    "fetch_duration": res.response_time or 0.0,
                                    "drop_stats": drop_stats,  # Pass stats downstream
                                }
                                await work_queue.put((source, lines, metadata))

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
                            except Exception:
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
                        try:
                            await loop.run_in_executor(
                                None, quality_tracker.report_failure, source, safe_error
                            )
                            batch_number = os.getenv("BATCH_NUMBER", "").strip()
                            batch_source = (
                                f"batch_{batch_number}" if batch_number else "pipeline"
                            )
                            await loop.run_in_executor(
                                None,
                                quality_tracker.record_run,
                                source,
                                {
                                    "timestamp": int(time.time()),
                                    "duration_ms": ((res.response_time or 0.0) * 1000),
                                    "fetched_count": 0,
                                    "working_count": 0,
                                    "geoip_json": "{}",
                                    "failure_modes_json": json.dumps(
                                        {"fetch_error": safe_error}
                                    ),
                                    "batch_source": batch_source,
                                },
                            )
                        except Exception:
                            pass
    except Exception as e:
        safe_error = SecurityValidator.sanitize_log_message(str(e))
        logger.error(f"Producer failed: {safe_error}")
    finally:
        # If absolutely nothing was provided, log a clear warning – this would
        # otherwise result in a silent zero-output run.
        if not sources and not proxies:
            logger.warning(
                "No sources or pre-supplied proxies provided - pipeline will produce zero results"
            )

        # Signal all consumers to exit
        for _ in range(num_consumers):
            await work_queue.put(None)
