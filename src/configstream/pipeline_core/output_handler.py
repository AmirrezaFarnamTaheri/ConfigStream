# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import asyncio
from pathlib import Path
from typing import List

from configstream.models import Proxy
from configstream.history.tracker import ProxyHistoryTracker
from configstream.output_logic import generate_categorized_outputs, save_metadata
from configstream.output_transport import save_json
from configstream.intelligence.washer.core import ProxyWasher
from configstream.intelligence.chaining import generate_smart_chains
from configstream.pipeline_core.stats import PipelineStats
from configstream.tagging import ProxyTagger
from configstream.config import AppSettings

logger = logging.getLogger(__name__)


async def generate_pipeline_outputs(
    optimized_proxies: List[Proxy],
    output_path: Path,
    stats: PipelineStats,
    history: ProxyHistoryTracker,
):
    """
    Orchestrates the generation of all pipeline outputs.
    Integrates Tagging, Washing, Smart Chaining, and File Generation.
    """
    logger.info("Starting final output generation phase...")

    # 0. Apply Tagging Strategy (Name formatting)
    # This applies user-defined or default naming templates to proxy remarks.
    # Must run BEFORE output generation so converters can use the formatted names.
    settings = AppSettings()
    rename_template = settings.RENAME_TEMPLATE
    if rename_template:
        logger.info(f"Applying proxy tagging with template: {rename_template}")
        tagger = ProxyTagger(rename_template)
        tagger.apply(optimized_proxies)
    else:
        logger.debug("No RENAME_TEMPLATE configured, skipping proxy tagging")

    # 1. Initialize Washer & Scanner (The Intelligence Layer)
    # We load keys from Env. If empty, washer degrades gracefully to no-op.
    washer = ProxyWasher(AppSettings().WARP_KEY_POOL)

    # [CRITICAL] Run the Go Scanner (Phase 2 Component)
    # This populates self.clean_ips in the washer with fresh, low-latency endpoints.
    # We await it because it's an async network operation.
    await washer.fetch_clean_ips()

    # Update stats with scanner results
    stats.scanner_ips_found = len(washer.clean_ips)

    # 2. Wash Batch (The "Blanket" Wash)
    # Generates standard WARP wraps for all working proxies (fallback/legacy behavior)
    # Returns the list of outbound configs and the set of IDs that were washed.
    # [FIX] Pass stats object for metrics instrumentation
    washed_outbounds, washed_ids, skip_reasons = washer.wash_batch(
        optimized_proxies, stats=stats
    )

    # Update stats with washing results
    stats.washer_success_count = len(washed_ids)

    # 3. Smart Chains (The Topology Router)
    # Generates complex chains (Intranet, IPv6, Streamer).
    # We pass the 'washer' instance so it can borrow the Clean IPs and Keys
    # to create "Washed Smart Chains" (3-hop).
    smart_chains = generate_smart_chains(optimized_proxies, washer=washer)

    # Update stats with smart chain counts (total number of chains generated)
    total_chains = sum(len(v) for v in smart_chains.values())
    stats.smart_chain_count = total_chains

    # 4. Generate Files (The Assembler)
    # Writes everything to disk: Sing-box (with chains), Clash (raw), Subs, etc.

    # Generate Master Proxies JSON with Rotation
    proxies_path = output_path / "proxies.json"
    old_proxies_path = output_path / "proxies.old.json"

    if proxies_path.exists():
        try:
            # Perform rotation for differential updates
            import shutil

            shutil.copy2(proxies_path, old_proxies_path)
            logger.info("Rotated proxies.json -> proxies.old.json for diff generation")
        except Exception as e:
            logger.warning(f"Failed to rotate proxies.json: {e}")

    # [FIX P2] Run blocking file I/O in executor
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_json, optimized_proxies, proxies_path)

    generated_files = await loop.run_in_executor(
        None,
        lambda: generate_categorized_outputs(
            optimized_proxies,
            output_path,
            washed_outbounds=washed_outbounds,
            washed_ids=washed_ids,
            smart_chains=smart_chains,
            washer=washer,
        ),
    )

    # 5. Metadata & Stats
    stats_dict = await stats.to_dict()

    await loop.run_in_executor(
        None, save_metadata, stats_dict, optimized_proxies, output_path
    )

    # [FIX] Export history visualization data
    # Ensure the history visualization JSON is generated for the frontend
    viz_path = output_path / "data" / "proxy_history_viz.json"
    viz_path.parent.mkdir(parents=True, exist_ok=True)
    await loop.run_in_executor(None, history.export_for_visualization, viz_path)

    # Also export active trend for analytics chart
    trend_path = output_path / "data" / "active_proxy_trend.json"
    await loop.run_in_executor(None, history.export_active_proxy_trend, trend_path)

    logger.info(f"Output generation complete. Files created in {output_path}")
    return generated_files
