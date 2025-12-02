import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from .setup_path import setup_python_path

setup_python_path()

from configstream.models import Proxy  # noqa: E402
from configstream.pipeline_core.sorter import sort_proxies_pareto  # noqa: E402

logger = logging.getLogger(__name__)


def load_and_merge_proxies(batch_dirs: List[Path]) -> Tuple[List[Proxy], int]:
    """
    Loads proxies from all batch directories, applying Last-Write-Wins strategy based on metadata.
    Returns (merged_proxies, total_processed_count).
    """
    # Map to store: config -> (proxy, timestamp)
    all_proxies_map = {}
    batches_with_timestamps = []

    # Global stats
    total_fetched_global = 0

    for batch_dir in batch_dirs:
        if not batch_dir.exists():
            logger.info(f"Info: Batch directory {batch_dir} not found. Skipping.")
            continue

        # Load metadata to get run timestamp and stats
        metadata_file = batch_dir / "metadata.json"
        timestamp = batch_dir.stat().st_mtime

        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    timestamp_str = metadata.get("last_updated_utc") or metadata.get(
                        "generated_at"
                    )
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(
                            timestamp_str.replace("Z", "+00:00")
                        ).timestamp()

                    # Accumulate fetched lines from metadata (if available)
                    # This provides accurate count of all lines processed, including failed ones
                    total_fetched_global += int(metadata.get("total_fetched", 0))

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(
                    f"Warning: Could not parse metadata in {batch_dir}: {e}. Using fallback."
                )

        batches_with_timestamps.append((batch_dir, timestamp))

    # Sort batches by timestamp (oldest first, so newest overwrites)
    batches_with_timestamps.sort(key=lambda x: x[1])

    logger.info(
        f"Processing {len(batches_with_timestamps)} batches in chronological order..."
    )

    total_processed = 0
    for batch_dir, batch_timestamp in batches_with_timestamps:
        proxies_file = batch_dir / "proxies.json"
        if not proxies_file.exists():
            proxies_file = batch_dir / "index.json"

        if not proxies_file.exists():
            logger.info(
                f"Info: Neither proxies.json nor index.json found in {batch_dir}. Skipping."
            )
            continue

        batch_name = batch_dir.name
        batch_source = batch_name.replace("output_batch_", "")

        with open(proxies_file, "r") as f:
            try:
                proxies_data = json.load(f)
                total_processed += len(proxies_data)
                for proxy_data in proxies_data:
                    proxy_data["batch_source"] = batch_source

                    # Ensure latency is float or None for proper sorting
                    if (
                        proxy_data.get("latency") == "0"
                        or proxy_data.get("latency") == 0
                    ):
                        proxy_data["latency"] = None

                    proxy = Proxy(**proxy_data)
                    all_proxies_map[proxy.config] = (proxy, batch_timestamp)

                logger.info(
                    f"Processed {batch_dir.name}: {len(proxies_data)} proxies at {datetime.fromtimestamp(batch_timestamp).isoformat()}"
                )
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(
                    f"Warning: Could not process {proxies_file}. Error: {e}. Skipping."
                )

    merged_proxies = [proxy for proxy, _ in all_proxies_map.values()]

    if not merged_proxies:
        logger.warning("⚠️ Warning: No proxies merged! Check input batch directories.")

    # Sort proxies by latency for consistent output
    merged_proxies.sort(key=lambda p: (p.latency is None, calculate_compound_score(p)))

    # If we accumulated global fetched counts from metadata, use that.
    # Otherwise fallback to total_processed (which is just working proxies).
    final_fetched_count = (
        total_fetched_global if total_fetched_global > 0 else total_processed
    )

    return merged_proxies, final_fetched_count
