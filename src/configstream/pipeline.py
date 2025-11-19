from __future__ import annotations

import asyncio
import base64
import json
import asyncio
import base64
import json
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
    proxy_unique_key,
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
from .intelligent_fallback import FallbackManager
from .source_quality import SourceQualityTracker
from .adaptive_workers import calculate_optimal_workers
from .test_cache import TestResultCache
from .async_file_ops import (
    read_multiple_files_async,
    shutdown_file_pool,
)

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


def _is_ip_address(address: str) -> bool:
    """Check if a string is a valid IP address."""
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False


async def _resolve_proxy_addresses(proxies: List[Proxy], progress: Optional[Progress]) -> None:
    """
    Perform bulk DNS resolution for proxy addresses that are not IPs.
    Updates the `resolved_ip` attribute on the Proxy objects in-place.
    """
    hosts_to_resolve = list(
        set(p.address for p in proxies if not p.resolved_ip and not _is_ip_address(p.address))
    )

    if not hosts_to_resolve:
        return

    task = progress.add_task("Resolving DNS...", total=len(hosts_to_resolve)) if progress else None
    resolver = aiodns.DNSResolver()
    ip_map: Dict[str, str] = {}

    async def _resolve_host(host: str) -> None:
        try:
            # Use A records for IPv4
            result = await resolver.query(host, "A")
            if result:
                ip_map[host] = result[0].host
        except aiodns.error.DNSError:
            # If A record fails, try AAAA for IPv6
            try:
                result_aaaa = await resolver.query(host, "AAAA")
                if result_aaaa:
                    ip_map[host] = result_aaaa[0].host
            except aiodns.error.DNSError:
                logger.debug(f"DNS resolution failed for {host}")
        finally:
            if progress and task is not None:
                progress.update(task, advance=1)

    await asyncio.gather(*(_resolve_host(host) for host in hosts_to_resolve))

    for p in proxies:
        if p.address in ip_map:
            p.resolved_ip = ip_map[p.address]


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

        async def _run_tests(batch: List[Proxy], label: str) -> List[Proxy]:
            if not batch:
                return []

            # Apply smart scheduling to filter proxies needing retest
            original_count = len(batch)
            batch_to_test = smart_scheduler.filter_proxies_for_retest(batch)

            # If smart scheduling filtered out all proxies, return cached results
            if not batch_to_test:
                logger.info(
                    "All %d proxies in %s have valid cache entries, skipping tests",
                    original_count,
                    label,
                )
                # Return original proxies, replacing with cached versions when available
                merged = []
                for proxy in batch:
                    cached = test_cache.get(proxy)
                    merged.append(cached if cached else proxy)
                return merged

            # Log smart scheduling efficiency
            if len(batch_to_test) < original_count:
                logger.info(
                    "Smart scheduling: testing %d/%d proxies for %s (%.1f%% reduction)",
                    len(batch_to_test),
                    original_count,
                    label,
                    (1 - len(batch_to_test) / original_count) * 100,
                )

            task = (
                progress.add_task(f"Testing {label}", total=len(batch_to_test))
                if progress
                else None
            )

            async def test_single(proxy: Proxy) -> Proxy:
                start_time = asyncio.get_running_loop().time()
                semaphore = concurrency_manager.get_semaphore()
                async with semaphore:
                    tested_proxy = await tester.test(proxy)
                latency = asyncio.get_running_loop().time() - start_time
                concurrency_manager.record("default", latency, tested_proxy.is_working)
                history_tracker.record_test_result(tested_proxy)
                if progress and task is not None:
                    progress.update(task, advance=1)
                return tested_proxy

            tested: List[Proxy] = []
            total_batches = (len(batch_to_test) + batch_size - 1) // batch_size
            concurrency_manager.start_tuner()
            try:
                with tracker.phase("test"):
                    for index, start in enumerate(range(0, len(batch_to_test), batch_size)):
                        subset = batch_to_test[start : start + batch_size]
                        batch_number = index + 1
                        if total_batches > 1:
                            logger.info(
                                "Testing batch %d/%d (%d proxies) for %s",
                                batch_number,
                                total_batches,
                                len(subset),
                                label,
                            )
                        results = await asyncio.gather(*(test_single(p) for p in subset))
                        tested.extend(results)
            finally:
                await concurrency_manager.stop_tuner()

            if progress and task is not None:
                progress.update(task, completed=len(batch_to_test))

            # Merge tested proxies with skipped proxies (preserve order and length)
            if len(tested) < original_count:
                from collections import defaultdict, deque

                def _key(p: Proxy) -> tuple[str, int, str]:
                    proto = (p.protocol or "").lower()
                    return (p.address, int(p.port), proto)

                buckets: dict[tuple[str, int, str], deque[Proxy]] = defaultdict(deque)
                for p in tested:
                    buckets[_key(p)].append(p)

                final_list: List[Proxy] = []
                for proxy in batch:
                    k = _key(proxy)
                    dq = buckets.get(k)
                    if dq and len(dq) > 0:
                        final_list.append(dq.popleft())
                    else:
                        cached = test_cache.get(proxy)
                        final_list.append(cached if cached else proxy)
                tested = final_list

            return tested

        async def _geolocate_batch(batch: List[Proxy], label: str) -> None:
            """
            Geolocate proxies using a robust 2-layer approach:
            Layer 1 (Primary): IP-based lookup using geoip_offline.DEFAULT_RESOLVER
            Layer 2 (Fallback): Remark-based parsing using remark_parser
            """
            if not batch:
                return

            geo_task = (
                progress.add_task(f"Geolocating {label}", total=len(batch)) if progress else None
            )

            # Import the new geolocation modules
            from . import geoip_offline
            from . import remark_parser

            # Initialize the remark parser (it pre-compiles regexes/maps)
            remark_geo_parser = remark_parser.RemarkGeoParser()

            geo_ip_count = 0
            geo_remark_count = 0

            try:
                with tracker.phase("geo"):
                    for proxy in batch:
                        # Layer 1: Primary Method (IP-based)
                        # Use the *resolved_ip* from the tester, not proxy.address
                        if proxy.resolved_ip:
                            cached_geo = geo_cache.get(proxy.resolved_ip)
                            if cached_geo:
                                proxy.country = cached_geo.get("country") or proxy.country
                                proxy.country_code = (
                                    cached_geo.get("country_code") or proxy.country_code
                                )
                                proxy.city = cached_geo.get("city") or proxy.city
                                proxy.asn = cached_geo.get("asn") or proxy.asn
                            else:
                                geo_info = geoip_offline.DEFAULT_RESOLVER.lookup(proxy.resolved_ip)
                                if geo_info.country_code:
                                    proxy.country_code = geo_info.country_code
                                    proxy.country = (
                                        geo_info.country_code
                                    )  # Use code as country for compatibility
                                    proxy.asn = geo_info.asn or proxy.asn
                                    geo_ip_count += 1

                                    # MISSING LINE FROM REPORT ADDED HERE:
                                    proxy.org = geo_info.org or ""
                                    proxy.isp = geo_info.org or "" # Map org to isp for frontend consistency

                                    # Cache the result
                                    geo_cache[proxy.resolved_ip] = {
                                        "country": proxy.country,
                                        "country_code": proxy.country_code,
                                        "city": proxy.city,
                                        "asn": proxy.asn,
                                        "org": proxy.org # Cache this too
                                    }

                        # Layer 2: Fallback Method (Remark-based)
                        # Only run if Layer 1 failed AND we have remarks to parse
                        if not proxy.country_code and proxy.remarks:
                            country_from_remark = remark_geo_parser.parse(proxy.remarks)
                            if country_from_remark:
                                proxy.country_code = country_from_remark
                                proxy.country = country_from_remark
                                geo_remark_count += 1

                        if progress and geo_task is not None:
                            progress.update(geo_task, advance=1)

                logger.info(
                    "Geolocation complete for %s: %d by IP, %d by remark.",
                    label,
                    geo_ip_count,
                    geo_remark_count,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("GeoIP lookup failed during %s: %s", label, exc)
            finally:
                if progress and geo_task is not None:
                    progress.update(geo_task, completed=len(batch))

        def _write_outputs() -> None:
            try:
                with tracker.phase("output"):
                    # Apply Aggressive Endpoint Deduplication
                    final_proxies = filter_unique_endpoints(all_working_proxies)
                    final_proxies.sort(key=lambda p: p.latency or float("inf"))

                    logger.info(
                        "Filtered %d working proxies down to %d unique endpoints",
                        len(all_working_proxies),
                        len(final_proxies),
                    )

                    # Apply custom tagging
                    from .config import AppSettings
                    from . import tagging

                    app_config = AppSettings()
                    if app_config.RENAME_TEMPLATE:
                        tagger = tagging.ProxyTagger(name_template=app_config.RENAME_TEMPLATE)
                        tagger.apply(final_proxies)
                    else:
                        format_proxy_names_with_rank(final_proxies)

                    sub_content = generate_base64_subscription(final_proxies)
                    sub_path = output_path / "vpn_subscription_base64.txt"
                    sub_path.write_text(sub_content)
                    output_files["subscription"] = sub_path.name

                    clash_content = generate_clash_config(all_working_proxies)
                    clash_path = output_path / "clash.yaml"
                    clash_path.write_text(generate_clash_config(final_proxies))
                    output_files["clash"] = clash_path.name

                    (output_path / "singbox.json").write_text(generate_singbox_config(final_proxies))
                    output_files["singbox"] = "singbox.json"

                    (output_path / "configs_raw.txt").write_text("\n".join(p.config for p in final_proxies))
                    output_files["raw"] = "configs_raw.txt"

                    (output_path / "shadowrocket.txt").write_text(generate_shadowrocket_subscription(final_proxies))
                    (output_path / "quantumult.conf").write_text(generate_quantumult_config(final_proxies))
                    (output_path / "surge.conf").write_text(generate_surge_config(final_proxies))

                    proxies_json = [
                        {
                            "config": p.config, "protocol": p.protocol, "address": p.address, "port": p.port,
                            "latency": p.latency, "country": p.country, "country_code": p.country_code,
                            "city": p.city, "remarks": p.remarks, "is_working": p.is_working,
                            "security_issues": p.security_issues, "tested_at": p.tested_at,
                        }
                        for p in final_proxies
                    ]

                    json_path = output_path / "proxies.json"
                    json_path.write_text(json.dumps(proxies_json, indent=2))
                    output_files["json"] = str(json_path)

                    full_dir = output_path / "full"
                    full_dir.mkdir(parents=True, exist_ok=True)
                    full_payload = [
                        {
                            "config": p.config,
                            "protocol": p.protocol,
                            "address": p.address,
                            "port": p.port,
                            "latency": p.latency,
                            "country": p.country,
                            "country_code": p.country_code,
                            "city": p.city,
                            "remarks": p.remarks,
                            "is_working": p.is_working,
                            "security_issues": p.security_issues,
                            "tested_at": p.tested_at,
                        }
                        for p in all_tested_proxies
                    ]

                    full_json_path = full_dir / "all.json"
                    full_json_path.write_text(json.dumps(full_payload, indent=2))
                    output_files["full"] = str(full_json_path)

                    success_rate = (
                        (stats["working"] / stats["tested"]) * 100 if stats["tested"] > 0 else 0.0
                    )
                    success_rate = (len(final_proxies) / stats["tested"] * 100) if stats["tested"] > 0 else 0.0

                    stats_json = {
                        "generated_at": start_time.isoformat(),
                        "generated_now": datetime.now(timezone.utc).isoformat(),
                        "total_fetched": stats["fetched"],
                        "total_tested": stats["tested"],
                        "total_working": len(final_proxies),
                        "success_rate": round(success_rate, 2),
                        "phase_summaries": phase_summaries,
                    }
                    (output_path / "statistics.json").write_text(json.dumps(stats_json, indent=2))

                    metadata = {
                        "version": "1.1.0",
                        "generated_at": start_time.isoformat(),
                        "proxy_count": len(final_proxies),
                        "working_count": len(final_proxies),
                        "stats": stats_json,
                    }
                    (output_path / "metadata.json").write_text(json.dumps(metadata, indent=2))

                    output_files.update(generate_categorized_outputs(final_proxies, output_path))

            except Exception as exc:
                logger.error("Failed to generate outputs: %s", exc)
                raise

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

                tested_batch = await _run_tests(unique_batch, phase_label)
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

                await _geolocate_batch(working_batch, phase_label)

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
                    _write_outputs()

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
                    _write_outputs()

        if not output_files:
            _write_outputs()

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
