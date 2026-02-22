# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Producer module: Fetches proxies from local files and remote URLs.
"""

import asyncio
import logging
import random
from functools import partial
from typing import List, Optional

from configstream.config import AppSettings
from configstream.extraction import extract_config_lines
from configstream.fetcher import fetch_multiple_sources
from configstream.security_validator import SecurityValidator
from configstream.source_quality import SourceQualityTracker
from configstream.intelligence.anomaly import AnomalyDetector

logger = logging.getLogger(__name__)


async def _report_source_failure(
    loop, quality_tracker, source, error_type, duration_ms=0.0, failure_modes=None
):
    """Helper to report failures to the quality tracker."""
    try:
        await loop.run_in_executor(
            None,
            quality_tracker.report_failure,
            source,
            error_type,
            duration_ms,
            failure_modes,
        )
    except Exception:  # nosec
        pass


async def produce_proxies(
    sources: List[str],
    proxies: List[str],  # Pre-supplied proxy lines
    work_queue: asyncio.Queue,
    settings: AppSettings,
    stop_event: asyncio.Event,
    quality_tracker: SourceQualityTracker,
    num_consumers: int,
    progress=None,
    task_fetch=None,
    event_stream=None,
) -> None:
    """
    Fetches raw proxy lines from sources and puts them into the work_queue.
    """
    loop = asyncio.get_running_loop()

    # Initialize Anomaly Detector (singleton or per-run)
    # Assuming AnomalyDetector can be instantiated or we get a singleton.
    # The original code seemed to have 'anomaly_detector' in scope or global.
    # Based on usage: 'anomaly_detector.is_safe'.
    # We'll instantiate it here.
    anomaly_detector = AnomalyDetector()
    enable_anomaly_detection = settings.ENABLE_ANOMALY_DETECTION

    try:
        # A. Handle Pre-supplied Proxies (CLI args or API input)
        if proxies:
            logger.info(f"Processing {len(proxies)} pre-supplied proxy lines...")
            # Treat as a "manual" source
            lines, drop_stats = await loop.run_in_executor(
                None, extract_config_lines, "\n".join(proxies), "manual_input"
            )
            if lines:
                await work_queue.put(("manual_input", lines, {"drop_stats": drop_stats}))

        # B. Handle Local Files
        local_files = [s for s in sources if s.startswith("file://") or "://" not in s]
        remote_urls = [s for s in sources if "://" in s and not s.startswith("file://")]

        if local_files:
            logger.info(f"Reading {len(local_files)} local files...")
            for fpath in local_files:
                if stop_event.is_set():
                    break

                safe_source = SecurityValidator.sanitize_log_message(fpath)

                # Queue Control (Drop-Tail) for Local Files
                if work_queue.maxsize > 0:
                    usage = work_queue.qsize() / work_queue.maxsize
                    if usage > 0.8:
                        logger.warning(
                            f"Queue overload ({usage:.1%}), dropping local file {safe_source}"
                        )
                        continue

                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Failed to read local file {safe_source}: {e}")
                    continue

                extract_func = partial(
                    extract_config_lines, content, source_url=fpath
                )
                file_lines, drop_stats = await loop.run_in_executor(None, extract_func)

                if file_lines:
                    metadata: dict[str, object] = {"drop_stats": drop_stats}
                    await work_queue.put((fpath, file_lines, metadata))
                else:
                    await _report_source_failure(
                        loop,
                        quality_tracker,
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
                    jitter = random.uniform(0.5, 2.0)  # nosec
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
                                source,
                                "no_valid_lines",
                                duration_ms=(res.response_time or 0.0) * 1000,
                                failure_modes=drop_stats,
                            )
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

                                # Queue Control (Drop-Tail)
                                if work_queue.maxsize > 0:
                                    usage = work_queue.qsize() / work_queue.maxsize
                                    if usage > 0.8:
                                        logger.warning(
                                            f"Queue overload ({usage:.1%}), dropping {count} lines from {safe_source}"
                                        )
                                        # Skip putting into queue
                                        continue

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
                            except Exception:  # nosec
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
                            source,
                            safe_error,
                            duration_ms=(res.response_time or 0.0) * 1000,
                            failure_modes={"fetch_error": safe_error},
                        )
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
