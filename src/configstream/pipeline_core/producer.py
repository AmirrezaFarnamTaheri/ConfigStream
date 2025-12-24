import asyncio
import logging
from typing import List, Optional, TYPE_CHECKING
from rich.progress import Progress, TaskID

from ..models import Proxy
from ..config import AppSettings
from ..fetcher import fetch_multiple_sources
from ..async_file_ops import read_multiple_files_async
from ..parsers import _extract_config_lines
from ..source_quality import SourceQualityTracker
from ..anomaly import AnomalyDetector
from ..security_validator import SecurityValidator

if TYPE_CHECKING:
    from ..event_stream import EventStream

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
):
    settings = AppSettings()
    try:
        # A. Handle Pre-supplied Proxies
        if proxies:
            supplied_lines = [p.config for p in proxies if p.config]
            if supplied_lines:
                await work_queue.put(("supplied-proxies", supplied_lines, {}))

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
                # [FIX] Handle new tuple return signature
                file_lines, _ = _extract_config_lines(content)
                if file_lines:
                    await work_queue.put((fpath, file_lines, {}))
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
                await work_queue.put(("supplied-config", [s], {}))
            elif s.startswith("ssconf://"):
                remote_urls.append(s.replace("ssconf://", "https://"))

        active_urls = []
        blocked_urls = []

        loop = asyncio.get_running_loop()
        sem = asyncio.Semaphore(100)  # Increased from 50 to 100 for better concurrency

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
            # Log specific reasons for blockage
            for url in blocked_urls:
                safe_url = SecurityValidator.sanitize_log_message(url)
                logger.info(f"Source blocked/cooldown: {safe_url}")

        if active_urls:
            logger.info(
                f"Starting fetch for {len(active_urls)} active sources "
                f"(Batch Size: 100, Concurrent Limit: {settings.PER_HOST_MAX_CONCURRENCY})"
            )
            batch_size = 100  # Increased from 50 to 100 for better throughput
            for i in range(0, len(active_urls), batch_size):
                # Add jitter to prevent overwhelming remote servers or rate limits
                if i > 0:
                    import random

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
                )

                for source, res in results.items():
                    if res.success and res.content:
                        # [FIX] Offload parsing to executor and handle stats
                        lines, drop_stats = await loop.run_in_executor(
                            None, _extract_config_lines, res.content
                        )
                        count = len(lines)
                        safe_source = SecurityValidator.sanitize_log_message(source)

                        if count == 0:
                            # Log that we got content but no proxies (useful for debugging invalid formats)
                            logger.warning(
                                "Source %s returned content (size=%d) but no valid config lines found. "
                                "Drop Stats: %s",
                                safe_source,
                                len(res.content) if res.content else 0,
                                drop_stats,
                            )
                            continue

                        # Offload anomaly check to executor to avoid blocking on DB/ML
                        is_safe, reason = await loop.run_in_executor(
                            None, anomaly_detector.is_safe, source, count
                        )

                        if is_safe:
                            if lines:
                                logger.debug(
                                    f"Anomaly check passed for {safe_source} (Count: {count})"
                                )
                                # Offload record to executor
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
                                    "drop_stats": drop_stats,  # [FIX] Pass stats downstream
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
                            if event_stream:
                                event_stream.emit(
                                    "fetch_blocked",
                                    f"Blocked source {safe_source}: {reason}",
                                )
                    else:
                        safe_source = SecurityValidator.sanitize_log_message(source)
                        logger.warning(
                            f"Failed to fetch {safe_source}: {res.error} "
                            f"(Status: {res.status_code})"
                        )
    except Exception as e:
        logger.error(f"Producer failed: {e}")
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
