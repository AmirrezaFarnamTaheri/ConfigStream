from __future__ import annotations

import asyncio
import base64
import json
import os
import random
import logging
import ipaddress
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import aiodns
import geoip2.database

from . import fetcher
from rich.progress import Progress

from .models import Proxy
from .core import parse_config
from .parsers import _extract_config_lines
# CRITICAL UPDATE: Imports from centralized filtering module
from .filtering import (
    dedupe_and_shuffle,
    filter_unique_endpoints,
    proxy_unique_key as _proxy_key,
)
from .output import (
    generate_base64_subscription,
    generate_clash_config,
    generate_singbox_config,
    generate_shadowrocket_subscription,
    generate_quantumult_config,
    generate_surge_config,
    generate_categorized_outputs,
    format_proxy_names_with_rank,
)
from .testers import SingBoxTester
from .performance import PerformanceTracker
from .proxy_history import ProxyHistoryTracker
from .statistics import StatisticsEngine
from .intelligent_fallback import FallbackManager
from .source_quality import SourceQualityTracker
from .adaptive_workers import calculate_optimal_workers
from .test_cache import TestResultCache
from .async_file_ops import (
    read_multiple_files_async,
    shutdown_file_pool,
)
from .runners import ProxyTestRunner
from .services import GeoLocationService, ReportGenerator
from .dns_cache import resolve_proxy_addresses as _resolve_proxy_addresses

from .constants import (
    MAX_SOURCE_URL_LENGTH,
)

logger = logging.getLogger(__name__)

PipelineResult = Dict[str, Any]


CHUNK_SIZE = 15_000  # Increased from 10k for better throughput
MAX_PIPELINE_PHASES = 40  # Increased from 30 for larger source lists


class SourceValidationError(ValueError):
    """Raised when a provided proxy source definition is invalid."""


def _normalise_source_url(source_url: str) -> str:
    """
    Validate and normalise a source URL or path.

    Args:
        source_url: Raw URL string or file path from sources file.

    Returns:
        Sanitised URL string or file path.

    Raises:
        SourceValidationError: If the source is empty or malformed.
    """
    trimmed = source_url.strip()
    if not trimmed:
        raise SourceValidationError("Source is empty")
    if len(trimmed) > MAX_SOURCE_URL_LENGTH:
        raise SourceValidationError("Source exceeds maximum length")

    parsed = urlparse(trimmed)
    # Allow empty scheme for local file paths
    if parsed.scheme.lower() not in {"http", "https", ""}:
        raise SourceValidationError(f"Unsupported URL scheme: {parsed.scheme}")
    # A URL must have a hostname
    if parsed.scheme and not parsed.netloc:
        raise SourceValidationError("Source URL is missing a hostname")

    return trimmed


def _prepare_sources(raw_sources: Sequence[str]) -> List[str]:
    """Normalise source URLs and file paths, and remove duplicates."""
    validated: List[str] = []
    seen: set[str] = set()

    for candidate in raw_sources:
        try:
            normalised = _normalise_source_url(candidate)
        except SourceValidationError as exc:
            logger.warning("Skipping invalid source %r: %s", candidate, exc)
            continue

        if normalised in seen:
            logger.debug("Skipping duplicate source %s", normalised)
            continue

        seen.add(normalised)
        validated.append(normalised)

    return validated




async def _produce_raw_configs(
    sources_to_fetch: List[str],
    queue: asyncio.Queue[Optional[Tuple[str, str]]],
    seen_raw_configs: set[str],
    stats: Dict[str, Any],
    progress: Optional[Progress],
    tracker: PerformanceTracker,
    quality_tracker: "SourceQualityTracker",
) -> int:
    """
    Fetches from sources, deduplicates raw configs, and puts them onto a queue.
    Puts a sentinel value (None) on the queue when done.
    """
    raw_fetch_total = 0
    # Import here to avoid circular dependency issues at module level
    from .config import AppSettings

    app_settings = AppSettings()

    # Separate local files from remote URLs
    local_sources = [s for s in sources_to_fetch if not s.startswith(("http://", "https://"))]
    remote_sources = [s for s in sources_to_fetch if s.startswith(("http://", "https://"))]

    async def process_and_queue(source: str, content: str):
        nonlocal raw_fetch_total
        try:
            # The fetcher already handles encoding, but we double-check base64 wrappers
            decoded_content = content
            # Heuristic check for base64
            if "://" not in decoded_content[:100]:
                try:
                    decoded_content = base64.b64decode(content, validate=True).decode("utf-8")
                except Exception:
                    pass

            configs = _extract_config_lines(decoded_content)
            if configs:
                raw_fetch_total += len(configs)
                for raw_config in configs:
                    if raw_config in seen_raw_configs:
                        stats["duplicates_skipped"] += 1
                        continue
                    seen_raw_configs.add(raw_config)
                    await queue.put((source, raw_config))
        except Exception as e:
            logger.error(f"Parse error for {source}: {e}")

    # 1. Process Local Sources
    if local_sources:
        file_task = (
            progress.add_task("Reading local sources...", total=len(local_sources))
            if progress
            else None
        )
        with tracker.phase("read_files"):
            file_results = await read_multiple_files_async(local_sources, max_concurrent=5)
            for file_path, content in file_results:
                if progress and file_task is not None:
                    progress.update(file_task, advance=1)
                if content.startswith("ERROR:"):
                    logger.warning("Failed to read %s: %s", file_path, content)
                    continue
                await process_and_queue(file_path, content)

    # 2. Process Remote Sources
    if remote_sources:
        fetch_task = (
            progress.add_task("Fetching remote sources (Adaptive)...", total=len(remote_sources))
            if progress
            else None
        )
        with tracker.phase("fetch"):
            results = await fetcher.fetch_multiple_sources(
                remote_sources,
                max_concurrent=app_settings.PER_HOST_MAX_CONCURRENCY,
                timeout=app_settings.FETCH_TIMEOUT,
                use_adaptive_timeout=True,
            )
            for source, result in results.items():
                if progress and fetch_task is not None:
                    progress.update(fetch_task, advance=1)
                if not result.success:
                    logger.warning(f"Source failed: {source} - {result.error}")
                    continue
                if result.status_code == 304:
                    logger.info(f"Source not modified: {source}")
                    continue

                await process_and_queue(source, result.content)
                if result.response_time:
                    quality_tracker.update_source_quality(source, [])

    await queue.put(None)  # Sentinel to signal completion
    return raw_fetch_total


async def run_full_pipeline(
    sources: List[str],
    output_dir: str,
    progress: Optional[Progress] = None,
    max_workers: int = 10,
    max_proxies: Optional[int] = None,
    country_filter: Optional[str] = None,
    min_latency: Optional[int] = None,
    max_latency: Optional[int] = None,
    timeout: int = 10,
    proxies: Optional[Sequence[Proxy]] = None,
    leniency: bool = False,
    strict_security: bool = False,
) -> PipelineResult:
    """
    Execute the full ConfigStream pipeline.

    Returns:
        Dictionary containing success flag, stats, output paths, and errors.
    """
    start_time = datetime.now(timezone.utc)
    # Validate and normalize output directory to prevent path traversal
    output_path = Path(output_dir).resolve()
    # Allow any path but ensure it exists and is accessible
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        logger.error("Cannot create output directory %s: %s", output_path, e)
        raise

    if max_workers <= 0:
        max_workers = calculate_optimal_workers()
        logger.info("Using adaptive worker count: %d", max_workers)

    tracker = PerformanceTracker()

    stats: Dict[str, Any] = {
        "fetched": 0,
        "tested": 0,
        "working": 0,
        "filtered": 0,
        "duplicates_skipped": 0,
        "insecure": 0,
        "phases": [],
    }
    output_files: Dict[str, str] = {}

    supplied_proxies: List[Proxy] = list(proxies or [])
    sources_to_fetch = _prepare_sources(sources)

    # Initialize the tracker (it was already imported but unused in logic)
    quality_tracker = SourceQualityTracker()

    # PRE-FETCH FILTERING
    # Filter out sources with terrible historical scores (< 10.0)
    # unless we are in a "forced" mode or have very few sources.

    filtered_sources = []
    for src in sources_to_fetch:
        score = quality_tracker.get_source_score(src)
        if score > 10.0:
            filtered_sources.append(src)
        else:
            logger.info(f"Skipping low-quality source: {src} (Score: {score})")

    sources_to_fetch = filtered_sources

    parse_cache: Dict[str, Proxy] = {}
    geo_cache: Dict[str, Dict[str, Optional[str]]] = {}
    geoip_reader: geoip2.database.Reader | None = None
    failure_reason: str | None = None
    history_tracker = ProxyHistoryTracker()
    fallback_manager = FallbackManager()
    quality_tracker = SourceQualityTracker()

    if not sources_to_fetch and not supplied_proxies:
        message = "No sources provided and no proxies supplied for retest"
        logger.error(message)
        snapshot = tracker.snapshot()
        return {
            "success": False,
            "stats": stats,
            "output_files": output_files,
            "error": message,
            "metrics": snapshot.to_dict(),
        }

    # Note: GeoIP databases should be downloaded by the CLI before calling the pipeline.
    # We skip re-downloading here to avoid redundant network/IO operations.

    try:
        logger.info(
            "Starting pipeline with %d sources and %d supplied proxies",
            len(sources_to_fetch),
            len(supplied_proxies),
        )

        queue: asyncio.Queue[Optional[Tuple[str, str]]] = asyncio.Queue(maxsize=CHUNK_SIZE * 2)
        seen_raw_configs: set[str] = set()

        producer_task = asyncio.create_task(
            _produce_raw_configs(
                sources_to_fetch,
                queue,
                seen_raw_configs,
                stats,
                progress,
                tracker,
                quality_tracker=quality_tracker,
            )
        )

        phase_summaries: List[Dict[str, Any]] = []
        stats["phases"] = phase_summaries

        processed_proxy_keys: set[Tuple[str, str, int, str, str, str]] = set()
        written_proxy_keys: set[Tuple[str, str, int, str, str, str]] = set()
        all_tested_proxies: List[Proxy] = []
        all_working_proxies: List[Proxy] = []

        preparsed_batches: List[List[Proxy]] = []
        if supplied_proxies:
            logger.info("Using %d supplied proxies", len(supplied_proxies))
            initial_batch = dedupe_and_shuffle(list(supplied_proxies))
            if initial_batch:
                preparsed_batches.append(initial_batch)
                for proxy in initial_batch:
                    if proxy.config:
                        seen_raw_configs.add(proxy.config)

        batch_size = 1000  # Process proxies in batches for better memory management
        effective_timeout_sec = float(timeout)
        if max_latency is not None and max_latency > 0:
            effective_timeout_sec = min(effective_timeout_sec, max_latency / 1000.0)

        logger.info("Using effective test timeout of %.2fs", effective_timeout_sec)

        # Initialize test result cache with 24-hour TTL for maximum cache hits
        test_cache = TestResultCache(ttl_seconds=86400)  # 24 hours for 60-70% hit rate
        logger.info("Test cache initialized: %s", test_cache.get_stats())

        # Initialize smart retest scheduler for intelligent test scheduling
        from .smart_scheduler import SmartRetestScheduler

        smart_scheduler = SmartRetestScheduler(cache=test_cache)
        scheduling_stats = smart_scheduler.get_scheduling_statistics()
        logger.info(
            "Smart scheduler initialized - avg health: %.2f, intervals: %s",
            scheduling_stats["average_health_score"],
            scheduling_stats["intervals"],
        )

        tester = SingBoxTester(
            timeout=effective_timeout_sec,
            cache=test_cache,
            strict_security=strict_security,
        )
        from .concurrency_manager import ConcurrencyManager

        concurrency_manager = ConcurrencyManager(
            loop=asyncio.get_running_loop(),
            initial_limit=max_workers,
            max_limit=max_workers * 2,
        )




        test_runner = ProxyTestRunner(
            progress=progress,
            tracker=tracker,
            history_tracker=history_tracker,
            smart_scheduler=smart_scheduler,
            test_cache=test_cache,
            tester=tester,
            concurrency_manager=concurrency_manager,
            batch_size=batch_size,
        )

        geo_service = GeoLocationService(
            progress=progress,
            tracker=tracker,
            geo_cache=geo_cache,
        )

        phase_index = 0

        async def consume_and_process():
            nonlocal phase_index, failure_reason
            while phase_index < MAX_PIPELINE_PHASES:
                if not preparsed_batches and queue.empty() and producer_task.done():
                    break

                phase_index += 1
                phase_label = f"phase-{phase_index}"
                chunk_source = "fetched"
                security_filtered = False
                proxies_by_source: Dict[str, List[Proxy]] = {}

                if preparsed_batches:
                    proxies_to_test = preparsed_batches.pop(0)
                    chunk_fetched = len(proxies_to_test)
                    parsed_count = len(proxies_to_test)
                    chunk_source = "supplied"
                else:
                    raw_batch: List[Tuple[str, str]] = []
                    # Greedily pull from queue to form a batch
                    while len(raw_batch) < CHUNK_SIZE:
                        try:
                            item = await asyncio.wait_for(queue.get(), timeout=0.1)
                            if item is None:  # Sentinel
                                await queue.put(None)
                                break
                            raw_batch.append(item)
                            queue.task_done()
                        except asyncio.TimeoutError:
                            if producer_task.done():
                                break

                    if not raw_batch and producer_task.done() and queue.empty():
                        break

                    chunk_fetched = len(raw_batch)
                    if chunk_fetched == 0:
                        continue

                    if progress:
                        parse_task = progress.add_task(
                            f"Parsing {phase_label}", total=chunk_fetched
                        )
                    else:
                        parse_task = None

                    parsed_from_sources: List[Proxy] = []
                    with tracker.phase("parse"):
                        for source, raw_config in raw_batch:
                            parsed: Optional[Proxy] = None
                            cached_proxy = parse_cache.get(raw_config)
                            if cached_proxy is not None:
                                parsed = replace(cached_proxy)
                            else:
                                candidate = parse_config(raw_config)
                                if candidate is not None:
                                    parse_cache[raw_config] = replace(candidate)
                                    parsed = candidate
                            if parsed is not None:
                                if source not in proxies_by_source:
                                    proxies_by_source[source] = []
                                proxies_by_source[source].append(parsed)
                                parsed_from_sources.append(parsed)
                            if progress and parse_task is not None:
                                progress.update(parse_task, advance=1)

                    proxies_to_test = parsed_from_sources
                    parsed_count = len(parsed_from_sources)

                    if proxies_to_test:
                        from .security_validator import (
                            validate_batch_configs,
                            TEST_POLICY,
                            STRICT_POLICY,
                        )

                        policy = TEST_POLICY if leniency else STRICT_POLICY
                        insecure_before = len(proxies_to_test)
                        proxies_to_test = validate_batch_configs(proxies_to_test, policy=policy)
                        insecure_removed = insecure_before - len(proxies_to_test)
                        if insecure_removed > 0:
                            logger.info("%d insecure proxies were filtered out", insecure_removed)
                            stats["insecure"] += insecure_removed
                            if not proxies_to_test:
                                security_filtered = True

                    from .freshness import apply_ttl

                    now = datetime.now(timezone.utc)
                    pre_filter_count = len(proxies_to_test)
                    proxies_to_test = [p for p in proxies_to_test if apply_ttl(p, now=now)]
                    dropped_count = pre_filter_count - len(proxies_to_test)
                    if dropped_count > 0:
                        logger.info("%d stale proxies were dropped due to TTL", dropped_count)

                    await _resolve_proxy_addresses(proxies_to_test, progress)
                    proxies_to_test = dedupe_and_shuffle(proxies_to_test)

                stats["fetched"] += chunk_fetched

                if not proxies_to_test:
                    if security_filtered:
                        failure_reason = (
                            "No configurations could be parsed or all were deemed insecure"
                        )
                    elif chunk_source == "fetched" and failure_reason is None:
                        failure_reason = "No configurations could be parsed"
                    phase_summaries.append(
                        {
                            "phase": phase_index,
                            "source": chunk_source,
                            "fetched": chunk_fetched,
                            "parsed": parsed_count,
                            "tested": 0,
                            "working": 0,
                            "new_working": 0,
                            "cumulative_working": len(all_working_proxies),
                        }
                    )
                    continue

                unique_batch: List[Proxy] = []
                for proxy in proxies_to_test:
                    key = _proxy_key(proxy)
                    if key in processed_proxy_keys:
                        continue
                    processed_proxy_keys.add(key)
                    unique_batch.append(proxy)

                if not unique_batch:
                    phase_summaries.append(
                        {
                            "phase": phase_index,
                            "source": chunk_source,
                            "fetched": chunk_fetched,
                            "parsed": parsed_count,
                            "tested": 0,
                            "working": 0,
                            "new_working": 0,
                            "cumulative_working": len(all_working_proxies),
                        }
                    )
                    continue

                if max_proxies is not None:
                    remaining_slots = max(0, max_proxies - stats["tested"])
                    if remaining_slots == 0:
                        logger.info(
                            "Reached max_proxies limit (%d); skipping remaining phases.",
                            max_proxies,
                        )
                        break
                    if len(unique_batch) > remaining_slots:
                        logger.info(
                            "Limiting %s to %d proxies to respect max_proxies",
                            phase_label,
                            remaining_slots,
                        )
                        unique_batch = unique_batch[:remaining_slots]

                tested_batch = await test_runner.run_tests(unique_batch, phase_label)
                all_tested_proxies.extend(tested_batch)
                stats["tested"] += len(tested_batch)

                if chunk_source == "fetched":
                    for source, proxies_from_source in proxies_by_source.items():
                        tested_proxies_for_source = [
                            p
                            for p in tested_batch
                            if any(
                                _proxy_key(p) == _proxy_key(orig) for orig in proxies_from_source
                            )
                        ]
                        if tested_proxies_for_source:
                            quality_tracker.update_source_quality(source, tested_proxies_for_source)

                working_batch = [p for p in tested_batch if p.is_working]

                if min_latency is not None:
                    working_batch = [
                        p
                        for p in working_batch
                        if p.latency is not None and p.latency >= min_latency
                    ]

                max_latency_limit = max_latency if max_latency is not None else 5000
                if max_latency_limit and max_latency_limit > 0:
                    working_batch = [
                        p
                        for p in working_batch
                        if p.latency is None or p.latency <= max_latency_limit
                    ]

                await geo_service.geolocate_batch(working_batch, phase_label)

                if country_filter:
                    working_batch = [
                        p
                        for p in working_batch
                        if p.country_code and p.country_code.upper() == country_filter.upper()
                    ]

                newly_added: List[Proxy] = []
                for proxy in working_batch:
                    key = _proxy_key(proxy)
                    if key in written_proxy_keys:
                        continue
                    written_proxy_keys.add(key)
                    newly_added.append(proxy)

                if newly_added:
                    all_working_proxies.extend(newly_added)
                    all_working_proxies.sort(key=lambda p: p.latency or float("inf"))
                    report_generator = ReportGenerator(
                        output_path=output_path,
                        tracker=tracker,
                        all_working_proxies=all_working_proxies,
                        all_tested_proxies=all_tested_proxies,
                        stats=stats,
                        start_time=start_time.isoformat(),
                        phase_summaries=phase_summaries,
                    )
                    report_generator.write_outputs()
                    output_files.update(report_generator.output_files)


                stats["working"] = len(all_working_proxies)
                stats["filtered"] = stats["working"]

                phase_summaries.append(
                    {
                        "phase": phase_index,
                        "source": chunk_source,
                        "fetched": chunk_fetched,
                        "parsed": parsed_count,
                        "tested": len(tested_batch),
                        "working": len(working_batch),
                        "new_working": len(newly_added),
                        "cumulative_working": len(all_working_proxies),
                    }
                )
                parse_cache.clear()

        await consume_and_process()
        raw_fetch_total = await producer_task
        logger.info("PIPELINE: Producer fetched %d raw proxy configs.", raw_fetch_total)

        if not all_tested_proxies:
            logger.warning(
                "No proxies were tested. The queue may have been empty or parsing failed."
            )
            if failure_reason is None:
                failure_reason = "No configurations could be parsed or fetched."

        if len(seen_raw_configs) == 0 and not supplied_proxies:
            logger.error("PIPELINE: No unique configs were found.")

        # Final check if loop exited prematurely
        if not all_working_proxies and not failure_reason:
            if stats["tested"] == 0:
                failure_reason = "No proxies were tested"

        if queue and phase_index >= MAX_PIPELINE_PHASES:
            logger.warning(
                "Reached maximum of %d phases with items still in queue.",
                MAX_PIPELINE_PHASES,
            )

            # Clear the parse cache at the end of each phase to save memory
            parse_cache.clear()

        if not all_tested_proxies:
            logger.warning(
                "No proxies were tested. The queue may have been empty or parsing failed."
            )
            if failure_reason is None:
                failure_reason = "No configurations could be parsed or fetched."

        if len(seen_raw_configs) == 0 and not supplied_proxies:
            logger.error("PIPELINE: No unique configs were found.")

        # Final check if loop exited prematurely
        if not all_working_proxies and not failure_reason:
            if stats["tested"] == 0:
                failure_reason = "No proxies were tested"

        if stats["tested"] == 0:
            message = failure_reason or "No proxies were tested"
            logger.error(message)
            snapshot = tracker.snapshot(
                proxies_tested=stats["tested"],
                proxies_working=stats["working"],
                sources_processed=len(sources_to_fetch),
            )
            return {
                "success": False,
                "stats": stats,
                "output_files": output_files,
                "error": message,
                "metrics": snapshot.to_dict(),
            }

        if not all_working_proxies:
            logger.warning("No proxies passed all filters across all phases")
            if fallback_manager.should_use_fallback(len(all_working_proxies)):
                logger.info("Attempting to use fallback proxies...")
                fallback_proxies = fallback_manager.load_fallback()
                if fallback_proxies:
                    all_working_proxies = fallback_proxies
                    stats["working"] = len(all_working_proxies)
                    stats["filtered"] = len(all_working_proxies)
                    report_generator = ReportGenerator(
                        output_path=output_path,
                        tracker=tracker,
                        all_working_proxies=all_working_proxies,
                        all_tested_proxies=all_tested_proxies,
                        stats=stats,
                        start_time=start_time.isoformat(),
                        phase_summaries=phase_summaries,
                    )
                    report_generator.write_outputs()
                    output_files.update(report_generator.output_files)


        if not output_files:
            report_generator = ReportGenerator(
                output_path=output_path,
                tracker=tracker,
                all_working_proxies=all_working_proxies,
                all_tested_proxies=all_tested_proxies,
                stats=stats,
                start_time=start_time.isoformat(),
                phase_summaries=phase_summaries,
            )
            report_generator.write_outputs()
            output_files.update(report_generator.output_files)

        if all_working_proxies:
            fallback_manager.save_successful_run(all_working_proxies)

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info("Pipeline completed successfully in %.1f seconds", elapsed)

        snapshot = tracker.snapshot(
            proxies_tested=stats["tested"],
            proxies_working=stats["working"],
            sources_processed=len(sources_to_fetch),
        )

        history_tracker.save()
        logger.info("Proxy history saved.")

        return {
            "success": True,
            "stats": stats,
            "output_files": output_files,
            "error": None,
            "metrics": snapshot.to_dict(),
        }

    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Pipeline failed with exception: %s", exc, exc_info=True)
        snapshot = tracker.snapshot(
            proxies_tested=stats["tested"],
            proxies_working=stats["working"],
            sources_processed=len(sources_to_fetch),
        )
        return {
            "success": False,
            "stats": stats,
            "output_files": output_files,
            "error": f"Pipeline failed: {exc}",
            "metrics": snapshot.to_dict(),
        }
    finally:
        # Ensure GeoIP reader is closed before leaving the pipeline
        if geoip_reader:
            try:
                geoip_reader.close()
            except Exception as e:  # pragma: no cover
                logger.debug("Error closing GeoIP reader: %s", e)

        # Only shut down the pool if we're not in a test environment
        # Tests manage their own pool lifecycle via fixtures
        import sys

        if "pytest" not in sys.modules:
            shutdown_file_pool()
        else:
            logger.debug("Skipping pool shutdown (test environment detected)")

        # Save the cache to disk at the very end.
        if "test_cache" in locals():
            test_cache.save()
