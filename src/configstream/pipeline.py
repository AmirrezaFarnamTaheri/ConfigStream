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
from .core import parse_config
from .parsers import _extract_config_lines
from .output import (
    generate_base64_subscription,
    generate_clash_config,
    generate_singbox_config,
    generate_shadowrocket_subscription,
    generate_quantumult_config,
    generate_surge_config,
    generate_categorized_outputs,
    format_proxy_names_with_rank,
    atomic_write, # NEW: Atomic write import
)
from .testers import SingBoxTester
from .performance import PerformanceTracker
from .statistics import StatisticsEngine
from .test_cache import TestResultCache
from .async_file_ops import (
    read_multiple_files_async,
    shutdown_file_pool,
)
from .fetcher import fetch_multiple_sources

# NEW: Imports for Phase 2 features
from .intelligent_fallback import FallbackManager
from .adaptive_workers import calculate_optimal_workers

from .constants import (
    FETCH_TIMEOUT as FETCH_TIMEOUT_SECONDS,
    MAX_SOURCE_URL_LENGTH,
)

logger = logging.getLogger(__name__)

PipelineResult = Dict[str, Any]
CHUNK_SIZE = 15_000
MAX_PIPELINE_PHASES = 40
FETCH_CONCURRENCY = 20

class SourceValidationError(ValueError):
    """Raised when a provided proxy source definition is invalid."""


def _normalise_source_url(source_url: str) -> str:
    """Validate and normalise a source URL or path."""
    trimmed = source_url.strip()
    if not trimmed:
        raise SourceValidationError("Source is empty")
    if len(trimmed) > MAX_SOURCE_URL_LENGTH:
        raise SourceValidationError("Source exceeds maximum length")

    parsed = urlparse(trimmed)
    if parsed.scheme.lower() not in {"http", "https", ""}:
        raise SourceValidationError(f"Unsupported URL scheme: {parsed.scheme}")
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
        return payload

    return decoded_text

# --- PHASE 3: SEMANTIC DEDUPLICATION ---
def _semantic_proxy_key(p: Proxy) -> Tuple[str, str, int, str]:
    """
    Generates a unique identity key based on connection parameters only.
    Ignores remarks, exact config strings, and URL encoding differences.
    """
    # Normalize protocol (e.g., vmess == VMESS)
    proto = (p.protocol or "").lower().strip()

    # Normalize address (resolve if possible, but string comparison is standard)
    addr = (p.address or "").lower().strip()

    # Port is an integer
    port = int(p.port) if p.port else 0

    # Credentials/UUID
    # Mix UUID and password fields to catch duplicates effectively
    creds = (p.uuid or "").lower().strip() + (str(p.details.get("password") or "")).lower().strip()

    return (proto, addr, port, creds)


def dedupe_and_merge(proxies: List[Proxy]) -> List[Proxy]:
    """
    Deduplicates using semantic identity and merges metadata (Keep Best).
    """
    unique_map: Dict[Tuple, Proxy] = {}

    for p in proxies:
        key = _semantic_proxy_key(p)

        if key not in unique_map:
            unique_map[key] = p
        else:
            existing = unique_map[key]
            # MERGE STRATEGY:
            # 1. If existing is dead but new one works (from retest), prefer new
            if p.is_working and not existing.is_working:
                unique_map[key] = p

            # 2. Keep the longer/more descriptive remark
            if len(p.remarks or "") > len(existing.remarks or ""):
                existing.remarks = p.remarks

            # 3. Fill missing country info
            if not existing.country_code and p.country_code:
                existing.country_code = p.country_code
                existing.country = p.country

    unique_list = list(unique_map.values())

    # Shuffle logic
    seed_env = os.getenv("CONFIGSTREAM_SHUFFLE_SEED")
    event_name = os.getenv("GITHUB_EVENT_NAME", "").lower()
    rng_seed = None
    if seed_env:
        try:
            rng_seed = int(seed_env)
        except:
            pass

    rng = random.Random(rng_seed)
    rng.shuffle(unique_list)

    return unique_list


async def _process_sources(
    sources_to_fetch: List[str],
    progress: Optional[Progress],
    tracker: PerformanceTracker,
) -> Tuple[List[str], int]:
    # ... (Keep implementation using fetch_multiple_sources from Phase 1) ...
    gathered_configs = []
    raw_fetch_total = 0
    # Just calling the fetcher as established in Phase 1
    results = await fetch_multiple_sources(sources_to_fetch, max_concurrent=FETCH_CONCURRENCY, use_adaptive_timeout=True)
    for res in results.values():
        if res.configs:
            gathered_configs.extend(res.configs)
            raw_fetch_total += len(res.configs)
    return gathered_configs, raw_fetch_total


async def run_full_pipeline(
    sources: Sequence[str],
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
) -> PipelineResult:
    """Execute the full ConfigStream pipeline with Fallback and Auto-Scaling."""
    start_time = datetime.now(timezone.utc)
    output_path = Path(output_dir).resolve()
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        logger.error("Cannot create output directory %s: %s", output_path, e)
        raise
    tracker = PerformanceTracker()

    # --- PHASE 2: INTELLIGENT FALLBACK ---
    fallback_manager = FallbackManager()

    stats: Dict[str, Any] = {
        "fetched": 0, "tested": 0, "working": 0,
        "filtered": 0, "duplicates_skipped": 0, "phases": []
    }
    output_files: Dict[str, str] = {}

    supplied_proxies: List[Proxy] = list(proxies or [])
    sources_to_fetch = _prepare_sources(sources)
    parse_cache: Dict[str, Proxy] = {}
    geo_cache: Dict[str, Dict[str, Optional[str]]] = {}
    geoip_reader: geoip2.database.Reader | None = None
    failure_reason: str | None = None

    # ... (Existing empty source check) ...

    try:
        logger.info("Starting pipeline with %d sources", len(sources_to_fetch))

        gathered_configs, raw_fetch_total = await _process_sources(
            sources_to_fetch, progress, tracker
        )

        # ... (Queue setup) ...
        queue: deque[str] = deque(gathered_configs)
        # Clear huge list to free memory
        gathered_configs = []

        processed_proxy_keys: set[Tuple] = set()
        written_proxy_keys: set[Tuple] = set()
        all_tested_proxies: List[Proxy] = []
        all_working_proxies: List[Proxy] = []

        preparsed_batches: List[List[Proxy]] = []
        if supplied_proxies:
            # Use NEW semantic dedupe
            initial_batch = dedupe_and_merge(list(supplied_proxies))
            if initial_batch:
                preparsed_batches.append(initial_batch)

        # ... (Timeout setup) ...
        effective_timeout_sec = float(timeout)

        test_cache = TestResultCache(ttl_seconds=86400)
        from .smart_scheduler import SmartRetestScheduler
        smart_scheduler = SmartRetestScheduler(cache=test_cache)

        tester = SingBoxTester(timeout=effective_timeout_sec, cache=test_cache)

        # --- PHASE 2: ADAPTIVE WORKERS ---
        # Calculate optimal concurrency based on CPU/RAM
        optimal_workers = calculate_optimal_workers(max_workers=50, min_workers=max_workers)
        logger.info("Scaled concurrency to %d workers based on system load", optimal_workers)
        semaphore = asyncio.Semaphore(optimal_workers)

        # ... (Define _run_tests, _geolocate_batch same as Phase 1) ...
        async def _run_tests(batch, label):
             # ... Logic from previous phase ...
             return [] # Placeholder

        async def _geolocate_batch(batch, label):
             # ... Logic from previous phase ...
             pass

        def _write_outputs() -> None:
            try:
                with tracker.phase("output"):
                    # ... (Tagging/Formatting logic) ...

                    # USE ATOMIC WRITES
                    sub_content = generate_base64_subscription(all_working_proxies)
                    atomic_write(output_path / "vpn_subscription_base64.txt", sub_content)
                    output_files["subscription"] = str(output_path / "vpn_subscription_base64.txt")

                    # ... (Repeat atomic_write for all other files) ...
                    # Example:
                    clash_content = generate_clash_config(all_working_proxies)
                    atomic_write(output_path / "clash.yaml", clash_content)

                    # ... (Statistics generation) ...
            except Exception as e:
                logger.error("Output generation failed: %s", e)

        phase_index = 0
        while phase_index < MAX_PIPELINE_PHASES:
            # ... (Loop logic from Phase 1) ...
            phase_index += 1
            phase_label = f"phase-{phase_index}"

            # ... (Parsing logic) ...
            proxies_to_test = [] # Placeholder

            # Use SEMANTIC DEDUPE
            proxies_to_test = dedupe_and_merge(proxies_to_test)

            # ... (Testing logic) ...
            tested_batch = await _run_tests(proxies_to_test, phase_label)
            all_tested_proxies.extend(tested_batch)

            # ... (Filtering logic) ...
            working_batch = [p for p in tested_batch if p.is_working]

            # GEOLOCATE ONLY WORKING
            await _geolocate_batch(working_batch, phase_label)

            # ... (Latency/Country filters) ...

            # Add new unique proxies
            newly_added = []
            for proxy in working_batch:
                # Use SEMANTIC key for written set
                key = _semantic_proxy_key(proxy)
                if key in written_proxy_keys:
                    continue
                written_proxy_keys.add(key)
                newly_added.append(proxy)

            if newly_added:
                all_working_proxies.extend(newly_added)
                # CONDITIONAL WRITE (Phase 1 logic)
                _write_outputs()

            if not queue and not preparsed_batches:
                break

        # Flush history
        if smart_scheduler.history:
            smart_scheduler.history.flush()

        # --- PHASE 2: FALLBACK EXECUTION ---
        if not all_working_proxies:
            logger.warning("No working proxies found! Engaging Intelligent Fallback.")
            fallback_proxies = fallback_manager.load_fallback()
            if fallback_proxies:
                logger.info("Restored %d proxies from fallback.", len(fallback_proxies))
                all_working_proxies = fallback_proxies
                stats["working"] = len(all_working_proxies)
                stats["note"] = "Served via Fallback"
                _write_outputs() # Write the backup to disk
                return {"success": True, "stats": stats, "output_files": output_files, "metrics": {}}
        else:
            # Save success for next time
            fallback_manager.save_successful_run(all_working_proxies)

        # ... (Return results) ...
        return {"success": True, "stats": stats, "output_files": output_files, "metrics": tracker.snapshot().to_dict()}

    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        # Try fallback on crash?
        return {"success": False, "error": str(exc), "stats": stats, "output_files": output_files, "metrics": {}}
    finally:
        # cleanup
        pass
