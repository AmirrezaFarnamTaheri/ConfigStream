from __future__ import annotations

import asyncio
import base64
import binascii
import json
import os
import random
import logging
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from collections import deque
from urllib.parse import urlparse

import httpx
import geoip2.database

from .http_client import get_client
from rich.progress import Progress

from .models import Proxy
from .core import geolocate_proxy, parse_config
from .parsers import _extract_config_lines
from .output import (
    generate_base64_subscription,
    generate_clash_config,
    generate_singbox_config,
    generate_shadowrocket_subscription,
    generate_quantumult_config,
    generate_surge_config,
    generate_categorized_outputs,
)
from .testers import SingBoxTester
from .performance import PerformanceTracker
from .statistics import StatisticsEngine
from .test_cache import TestResultCache
from .async_file_ops import (
    read_multiple_files_async,
    shutdown_file_pool,
)
from .geoip import download_geoip_dbs

from .constants import (
    FETCH_TIMEOUT as FETCH_TIMEOUT_SECONDS,
    MAX_SOURCE_URL_LENGTH,
)

logger = logging.getLogger(__name__)

PipelineResult = Dict[str, Any]


CHUNK_SIZE = 15_000  # Increased from 10k for better throughput
MAX_PIPELINE_PHASES = 40  # Increased from 30 for larger source lists
FETCH_CONCURRENCY = 20  # Optimized concurrent fetching


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


def _maybe_decode_base64(payload: str) -> str:
    """Attempt to decode base64-encoded payloads."""
    stripped = payload.strip()
    if not stripped:
        return ""
    if len(stripped) % 4 != 0:
        return payload

    try:
        decoded_bytes = base64.b64decode(stripped, validate=True)
        decoded_text = decoded_bytes.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return payload

    if decoded_text.count("\n") < 1 and payload.count("\n") > 1:
        # Heuristic: treat single-line decodes as false positives.
        return payload

    return decoded_text


# ==== BEGIN: de-dup + seeded shuffle helpers ====
def _proxy_key(p) -> Tuple[str, str, int, str, str]:
    """
    Build a stable identity for a proxy. Adjust fields if your Proxy model differs.
    """
    proto = (getattr(p, "protocol", "") or "").lower()
    addr = getattr(p, "address", "") or ""
    port = int(getattr(p, "port", 0) or 0)
    uuid = getattr(p, "uuid", "") or ""
    config = (getattr(p, "config", "") or "").strip()
    return (proto, addr, port, uuid, config)


def dedupe_and_shuffle(proxies: List) -> List:
    """
    Remove duplicates, then shuffle.
    Shuffling is deterministic on push/PR events (if CONFIGSTREAM_SHUFFLE_SEED is set)
    for reproducibility, and random on scheduled or manual runs to ensure variety.
    """
    seen = set()
    unique: List = []
    for p in proxies:
        k = _proxy_key(p)
        if k in seen:
            continue
        seen.add(k)
        unique.append(p)

    seed_env = os.getenv("CONFIGSTREAM_SHUFFLE_SEED")
    event_name = os.getenv("GITHUB_EVENT_NAME", "").lower()
    run_identifier = os.getenv("GITHUB_RUN_ID")

    rng_seed: int | str | None = None

    if event_name in {"push", "pull_request"} and seed_env:
        # Respect a configured seed to keep reproducibility in CI
        try:
            rng_seed = int(seed_env)
        except ValueError:
            rng_seed = seed_env
    elif event_name in {"schedule", "workflow_dispatch"}:
        # Ensure manual or scheduled runs still differ between executions.
        # Prefer the run identifier from GitHub; fall back to entropy.
        rng_seed = run_identifier or None
    elif seed_env:
        # Local overrides (e.g. developer runs) can still provide a seed.
        try:
            rng_seed = int(seed_env)
        except ValueError:
            rng_seed = seed_env

    rng = random.Random(rng_seed)
    rng.shuffle(unique)
    return unique


# ==== END: de-dup + seeded shuffle helpers ====


async def _fetch_source(client: httpx.AsyncClient, source_url: str) -> Tuple[List[str], int]:
    """Fetch a proxy list from a single source."""
    try:
        async with get_client(retries=3) as client:
            response = await client.get(source_url, timeout=FETCH_TIMEOUT_SECONDS)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch %s: %s", source_url, exc)
        return [], 0

    text = response.text
    if not text or not text.strip():
        logger.warning("Empty response from %s", source_url)
        return [], 0

    payload = _maybe_decode_base64(text)
    configs = _extract_config_lines(payload)

    if configs:
        logger.debug("Fetched %d configs from %s", len(configs), source_url)
    else:
        logger.info("No usable configurations found in %s", source_url)

    return configs, len(configs)


async def _fetch_and_parse_sources(
    sources: Sequence[str],
    progress: Optional[Progress] = None,
) -> Tuple[List[str], int]:
    """Fetch and parse proxy configurations from sources."""
    gathered_configs: List[str] = []
    raw_fetch_total = 0
    sources_to_fetch = _prepare_sources(sources)

    if not sources_to_fetch:
        return gathered_configs, raw_fetch_total

    local_sources = [s for s in sources_to_fetch if not s.startswith(("http://", "https://"))]
    remote_sources = [s for s in sources_to_fetch if s.startswith(("http://", "https://"))]

    if local_sources:
        if progress:
            file_task = progress.add_task("Reading local sources...", total=len(local_sources))
        file_results = await read_multiple_files_async(local_sources, max_concurrent=5)
        for file_path, content in file_results:
            if content.startswith("ERROR:"):
                logger.warning(f"Failed to read {file_path}: {content}")
                continue
            configs = _extract_config_lines(content)
            if configs:
                gathered_configs.extend(configs)
                raw_fetch_total += len(configs)
            if progress and file_task is not None:
                progress.update(file_task, advance=1)

    if remote_sources:
        if progress:
            fetch_task = progress.add_task("Fetching remote sources...", total=len(remote_sources))
        async with get_client() as client:
            results = await asyncio.gather(
                *(_fetch_source(client, source) for source in remote_sources),
                return_exceptions=True,
            )
        for source, result in zip(remote_sources, results):
            if isinstance(result, BaseException):
                logger.warning(f"Failed to fetch {source}: {result}")
                continue
            configs, count = result
            if configs:
                gathered_configs.extend(configs)
            raw_fetch_total += count
            if progress and fetch_task is not None:
                progress.update(fetch_task, advance=1)

    return gathered_configs, raw_fetch_total


async def run_full_pipeline(
    sources: Sequence[str],
    output_dir: str,
    progress: Optional[Progress] = None,
    max_workers: int = 10,  # noqa: ARG001 - reserved for future concurrency
    max_proxies: Optional[int] = None,
    country_filter: Optional[str] = None,
    min_latency: Optional[int] = None,
    max_latency: Optional[int] = None,
    timeout: int = 10,
    proxies: Optional[Sequence[Proxy]] = None,
    leniency: bool = False,
) -> PipelineResult:
    """
    Execute the full ConfigStream pipeline.

    Returns:
        Dictionary containing success flag, stats, output paths, and errors.
    """
    start_time = datetime.now(timezone.utc)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    tracker = PerformanceTracker()

    stats: Dict[str, Any] = {
        "fetched": 0,
        "tested": 0,
        "working": 0,
        "filtered": 0,
        "duplicates_skipped": 0,
        "phases": [],
    }
    output_files: Dict[str, str] = {}

    supplied_proxies: List[Proxy] = list(proxies or [])
    sources_to_fetch = _prepare_sources(sources)
    parse_cache: Dict[str, Proxy] = {}
    geo_cache: Dict[str, Dict[str, Optional[str]]] = {}
    geoip_reader: geoip2.database.Reader | None = None
    failure_reason: str | None = None

    if not sources and not supplied_proxies:
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

    # Ensure GeoIP databases are available before starting
    await download_geoip_dbs()

    try:
        logger.info(
            "Starting pipeline with %d sources and %d supplied proxies",
            len(sources),
            len(supplied_proxies),
        )

        gathered_configs, raw_fetch_total = await _fetch_and_parse_sources(
            sources, progress=progress
        )

        logger.info("PIPELINE: Fetched %d raw proxy configs.", raw_fetch_total)

        phase_summaries: List[Dict[str, Any]] = []
        stats["phases"] = phase_summaries

        queue: deque[str] = deque()
        seen_raw_configs: set[str] = set()
        for raw_config in gathered_configs:
            if raw_config.strip().startswith("ssr://"):
                logger.debug("Skipping unsupported ssr:// proxy")
                continue
            if raw_config in seen_raw_configs:
                stats["duplicates_skipped"] += 1
                continue
            seen_raw_configs.add(raw_config)
            queue.append(raw_config)

        gathered_configs.clear()

        logger.info("PIPELINE: Prepared %d unique configs for sequential processing.", len(queue))

        processed_proxy_keys: set[Tuple[str, str, int, str, str]] = set()
        written_proxy_keys: set[Tuple[str, str, int, str, str]] = set()
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

        tester = SingBoxTester(timeout=effective_timeout_sec, cache=test_cache)
        semaphore = asyncio.Semaphore(max(1, max_workers))

async def _test_proxies(
    proxies: List[Proxy],
    tester: SingBoxTester,
    semaphore: asyncio.Semaphore,
    progress: Optional[Progress] = None,
    batch_size: int = 1000,
    label: str = "proxies",
) -> List[Proxy]:
    """Test a list of proxies concurrently."""
    if not proxies:
        return []

    task = progress.add_task(f"Testing {label}", total=len(proxies)) if progress else None

    async def test_single(proxy: Proxy) -> Proxy:
        async with semaphore:
            tested_proxy = await tester.test(proxy)
        if progress and task is not None:
            progress.update(task, advance=1)
        return tested_proxy

    tested: List[Proxy] = []
    total_batches = (len(proxies) + batch_size - 1) // batch_size
    for index, start in enumerate(range(0, len(proxies), batch_size)):
        subset = proxies[start : start + batch_size]
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

    if progress and task is not None:
        progress.update(task, completed=len(proxies))

    return tested

async def _geolocate_batch(
    batch: List[Proxy],
    geoip_reader: Optional[geoip2.database.Reader],
    geo_cache: Dict[str, Dict[str, Optional[str]]],
    progress: Optional[Progress] = None,
    label: str = "proxies",
) -> None:
    """Geolocate a batch of proxies."""
    if not batch or not geoip_reader:
        return

    geo_task = progress.add_task(f"Geolocating {label}", total=len(batch)) if progress else None
    working_items = [proxy for proxy in batch if proxy.is_working]
    if working_items:
        for proxy in batch:
            if proxy.is_working:
                cached_geo = geo_cache.get(proxy.address)
                if cached_geo:
                    proxy.country = cached_geo.get("country") or proxy.country
                    proxy.country_code = cached_geo.get("country_code") or proxy.country_code
                    proxy.city = cached_geo.get("city") or proxy.city
                    proxy.asn = cached_geo.get("asn") or proxy.asn
                else:
                    await geolocate_proxy(proxy, geoip_reader)
                    if proxy.country_code not in {"", "XX"} or proxy.country != "Unknown":
                        geo_cache[proxy.address] = {
                            "country": proxy.country,
                            "country_code": proxy.country_code,
                            "city": proxy.city,
                            "asn": proxy.asn,
                        }
            if progress and geo_task is not None:
                progress.update(geo_task, advance=1)
    if progress and geo_task is not None:
        progress.update(geo_task, completed=len(batch))


def _generate_outputs(
    output_path: Path,
    all_working_proxies: List[Proxy],
    all_tested_proxies: List[Proxy],
    stats: Dict[str, Any],
    start_time: datetime,
    sources_to_fetch: List[str],
    phase_summaries: List[Dict[str, Any]],
) -> Dict[str, str]:
    """Generate all output files."""
    output_files: Dict[str, str] = {}
    try:
        sub_content = generate_base64_subscription(all_working_proxies)
        sub_path = output_path / "vpn_subscription_base64.txt"
        sub_path.write_text(sub_content)
        output_files["subscription"] = str(sub_path)

        clash_content = generate_clash_config(all_working_proxies)
        clash_path = output_path / "clash.yaml"
        clash_path.write_text(clash_content)
        output_files["clash"] = str(clash_path)

        try:
            singbox_content = generate_singbox_config(all_working_proxies)
            singbox_path = output_path / "singbox.json"
            singbox_path.write_text(singbox_content)
            output_files["singbox"] = str(singbox_path)
        except Exception as exc:
            logger.warning("Could not generate SingBox format: %s", exc)

        raw_content = "\n".join(p.config for p in all_working_proxies)
        raw_path = output_path / "configs_raw.txt"
        raw_path.write_text(raw_content)
        output_files["raw"] = str(raw_path)

        shadowrocket_content = generate_shadowrocket_subscription(all_working_proxies)
        shadowrocket_path = output_path / "shadowrocket.txt"
        shadowrocket_path.write_text(shadowrocket_content)
        output_files["shadowrocket"] = str(shadowrocket_path)

        quantumult_content = generate_quantumult_config(all_working_proxies)
        quantumult_path = output_path / "quantumult.conf"
        quantumult_path.write_text(quantumult_content)
        output_files["quantumult"] = str(quantumult_path)

        surge_content = generate_surge_config(all_working_proxies)
        surge_path = output_path / "surge.conf"
        surge_path.write_text(surge_content)
        output_files["surge"] = str(surge_path)

        proxies_json = [p.to_dict() for p in all_working_proxies]
        json_path = output_path / "proxies.json"
        json_path.write_text(json.dumps(proxies_json, indent=2))
        output_files["json"] = str(json_path)

        full_dir = output_path / "full"
        full_dir.mkdir(parents=True, exist_ok=True)
        full_payload = [p.to_dict() for p in all_tested_proxies]
        full_json_path = full_dir / "all.json"
        full_json_path.write_text(json.dumps(full_payload, indent=2))
        output_files["full"] = str(full_json_path)

        success_rate = (stats["working"] / stats["tested"]) * 100 if stats["tested"] > 0 else 0.0
        protocol_counts = {}
        for proxy in all_working_proxies:
            protocol_counts[proxy.protocol] = protocol_counts.get(proxy.protocol, 0) + 1
        working_with_latency = [
            proxy.latency for proxy in all_working_proxies if proxy.latency is not None
        ]
        average_latency = (
            sum(working_with_latency) / len(working_with_latency)
            if working_with_latency
            else 0.0
        )

        stats_json = {
            "generated_at": start_time.isoformat(),
            "generated_now": datetime.now(timezone.utc).isoformat(),
            "total_fetched": stats["fetched"],
            "total_tested": stats["tested"],
            "total_working": stats["working"],
            "total_filtered": stats["filtered"],
            "duplicates_skipped": stats["duplicates_skipped"],
            "success_rate": round(success_rate, 2),
            "average_latency_ms": round(average_latency, 2),
            "protocol_distribution": protocol_counts,
            "phase_summaries": phase_summaries,
            "cache_bust": int(datetime.now().timestamp() * 1000),
        }
        stats_path = output_path / "statistics.json"
        stats_path.write_text(json.dumps(stats_json, indent=2))
        output_files["statistics"] = str(stats_path)

        metadata = {
            "version": "1.0.0",
            "generated_at": start_time.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "proxy_count": len(all_working_proxies),
            "working_count": stats["working"],
            "source_count": len(sources_to_fetch),
            "tested_count": len(all_tested_proxies),
            "fallback_available": bool(all_tested_proxies) and not all_working_proxies,
            "phase_summaries": phase_summaries,
            "cache_bust": int(datetime.now().timestamp() * 1000),
            "stats": stats_json,
        }
        metadata_path = output_path / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))
        output_files["metadata"] = str(metadata_path)

        stats_report = StatisticsEngine(all_tested_proxies).generate_report()
        report_path = output_path / "report.json"
        report_path.write_text(json.dumps(stats_report, indent=2))
        output_files["report"] = str(report_path)

        try:
            categorized_files = generate_categorized_outputs(all_tested_proxies, output_path)
            output_files.update(categorized_files)
            logger.info("Generated %d categorized output files", len(categorized_files))
        except Exception as exc:
            logger.warning("Failed to generate categorized outputs: %s", exc)
    except Exception as exc:
        logger.error("Failed to generate outputs: %s", exc)
        raise
    return output_files

        phase_index = 0
        while phase_index < MAX_PIPELINE_PHASES:
            if not queue and not preparsed_batches:
                if failure_reason is None:
                    failure_reason = "No configurations could be parsed"
                break

            phase_index += 1
            phase_label = f"phase-{phase_index}"
            chunk_source = "fetched"
            security_filtered = False

            if preparsed_batches:
                proxies_to_test = preparsed_batches.pop(0)
                chunk_fetched = len(proxies_to_test)
                parsed_count = len(proxies_to_test)
                chunk_source = "supplied"
            else:
                raw_batch: List[str] = []
                while queue and len(raw_batch) < CHUNK_SIZE:
                    raw_batch.append(queue.popleft())

                chunk_fetched = len(raw_batch)
                if chunk_fetched == 0:
                    break

                chunk_source = "fetched"
                if progress:
                    parse_task = progress.add_task(f"Parsing {phase_label}", total=chunk_fetched)
                else:
                    parse_task = None

                parsed_from_sources: List[Proxy] = []
                with tracker.phase("parse"):
                    for raw_config in raw_batch:
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
                            parsed_from_sources.append(parsed)
                        if progress and parse_task is not None:
                            progress.update(parse_task, advance=1)

                proxies_to_test = parsed_from_sources
                parsed_count = len(parsed_from_sources)

                from .security_validator import validate_batch_configs

                if proxies_to_test:
                    insecure_before = len(proxies_to_test)
                    proxies_to_test = validate_batch_configs(proxies_to_test, leniency=leniency)
                    insecure_removed = insecure_before - len(proxies_to_test)
                    if insecure_removed > 0:
                        logger.info("%d insecure proxies were filtered out", insecure_removed)
                        if not proxies_to_test:
                            security_filtered = True

                proxies_to_test = dedupe_and_shuffle(proxies_to_test)

            stats["fetched"] += chunk_fetched

            if not proxies_to_test:
                if security_filtered:
                    failure_reason = "No configurations could be parsed or all were deemed insecure"
                elif chunk_source == "fetched" and failure_reason is None:
                    failure_reason = "No configurations could be parsed"
                phase_summary = {
                    "phase": phase_index,
                    "source": chunk_source,
                    "fetched": chunk_fetched,
                    "parsed": parsed_count,
                    "tested": 0,
                    "working": 0,
                    "new_working": 0,
                    "cumulative_working": len(all_working_proxies),
                }
                phase_summaries.append(phase_summary)
                stats["phases"] = phase_summaries
                continue

            unique_batch: List[Proxy] = []
            for proxy in proxies_to_test:
                key = _proxy_key(proxy)
                if key in processed_proxy_keys:
                    continue
                processed_proxy_keys.add(key)
                unique_batch.append(proxy)

            if not unique_batch:
                phase_summary = {
                    "phase": phase_index,
                    "source": chunk_source,
                    "fetched": chunk_fetched,
                    "parsed": parsed_count,
                    "tested": 0,
                    "working": 0,
                    "new_working": 0,
                    "cumulative_working": len(all_working_proxies),
                }
                phase_summaries.append(phase_summary)
                stats["phases"] = phase_summaries
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
            with tracker.phase("test"):
                tested_batch = await _test_proxies(
                    unique_batch,
                    tester=tester,
                    semaphore=semaphore,
                    progress=progress,
                    batch_size=batch_size,
                    label=phase_label,
                )
            try:
                geoip_db_path = Path("data/GeoLite2-City.mmdb")
                if geoip_reader is None and geoip_db_path.exists():
                    geoip_reader = geoip2.database.Reader(str(geoip_db_path))
                elif geoip_reader is None:
                    logger.warning("GeoIP database not found, skipping geolocation.")
                with tracker.phase("geo"):
                    await _geolocate_batch(
                        tested_batch,
                        geoip_reader=geoip_reader,
                        geo_cache=geo_cache,
                        progress=progress,
                        label=phase_label,
                    )
            except Exception as e:
                logger.error(f"Error during geolocation: {e}")

            all_tested_proxies.extend(tested_batch)
            stats["tested"] += len(tested_batch)

            if progress:
                filter_task = progress.add_task(f"Filtering {phase_label}", total=len(tested_batch))
            else:
                filter_task = None

            with tracker.phase("filter"):
                working_batch = [p for p in tested_batch if p.is_working]

                if country_filter:
                    working_batch = [
                        p
                        for p in working_batch
                        if p.country_code and p.country_code.upper() == country_filter.upper()
                    ]
                    logger.info(
                        "Filtered %s to %d proxies in %s",
                        phase_label,
                        len(working_batch),
                        country_filter,
                    )

                if min_latency is not None:
                    working_batch = [
                        p
                        for p in working_batch
                        if p.latency is not None and p.latency >= min_latency
                    ]
                    logger.info(
                        "Filtered %s to %d proxies with latency >= %dms",
                        phase_label,
                        len(working_batch),
                        min_latency,
                    )

                max_latency_limit = max_latency if max_latency is not None else 5000
                if max_latency_limit and max_latency_limit > 0:
                    working_batch = [
                        p
                        for p in working_batch
                        if p.latency is None or p.latency <= max_latency_limit
                    ]
                    logger.info(
                        "Filtered %s to %d proxies with latency <= %dms",
                        phase_label,
                        len(working_batch),
                        max_latency_limit,
                    )

            working_batch.sort(key=lambda p: p.latency or float("inf"))

            newly_added: List[Proxy] = []
            for proxy in working_batch:
                key = _proxy_key(proxy)
                if key in written_proxy_keys:
                    continue
                written_proxy_keys.add(key)
                newly_added.append(proxy)

            if newly_added:
                all_working_proxies.extend(newly_added)

            stats["working"] = len(all_working_proxies)
            stats["filtered"] = len(all_working_proxies)

            if progress and filter_task is not None:
                progress.update(filter_task, completed=len(tested_batch))

            if not working_batch and tested_batch:
                logger.warning(
                    "No working proxies detected in %s; keeping tested proxies as fallback",
                    phase_label,
                )

            phase_summary = {
                "phase": phase_index,
                "source": chunk_source,
                "fetched": chunk_fetched,
                "parsed": parsed_count,
                "tested": len(tested_batch),
                "working": len(working_batch),
                "new_working": len(newly_added),
                "cumulative_working": len(all_working_proxies),
            }
            phase_summaries.append(phase_summary)
            stats["phases"] = phase_summaries
            with tracker.phase("output"):
                output_files = _generate_outputs(
                    output_path=output_path,
                    all_working_proxies=all_working_proxies,
                    all_tested_proxies=all_tested_proxies,
                    stats=stats,
                    start_time=start_time,
                    sources_to_fetch=sources_to_fetch,
                    phase_summaries=phase_summaries,
                )

            if not queue and not preparsed_batches:
                break

        if queue and phase_index >= MAX_PIPELINE_PHASES:
            logger.warning(
                "Reached maximum of %d phases with %d configs still queued.",
                MAX_PIPELINE_PHASES,
                len(queue),
            )

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

        if not output_files:
            with tracker.phase("output"):
                output_files = _generate_outputs(
                    output_path=output_path,
                    all_working_proxies=all_working_proxies,
                    all_tested_proxies=all_tested_proxies,
                    stats=stats,
                    start_time=start_time,
                    sources_to_fetch=sources_to_fetch,
                    phase_summaries=phase_summaries,
                )

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info("Pipeline completed successfully in %.1f seconds", elapsed)

        snapshot = tracker.snapshot(
            proxies_tested=stats["tested"],
            proxies_working=stats["working"],
            sources_processed=len(sources_to_fetch),
        )

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
            geoip_reader.close()

        # Only shut down the pool if we're not in a test environment
        # Tests manage their own pool lifecycle via fixtures
        import sys

        if "pytest" not in sys.modules:
            shutdown_file_pool()
        else:
            logger.debug("Skipping pool shutdown (test environment detected)")
