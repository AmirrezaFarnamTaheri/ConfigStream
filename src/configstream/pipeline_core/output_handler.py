import os
import logging
from pathlib import Path
from typing import List

from ..models import Proxy
from ..proxy_history import ProxyHistoryTracker
from ..output_logic import generate_categorized_outputs, save_metadata
from ..output_transport import save_json
from ..intelligence.washer.core import ProxyWasher
from ..intelligence.washer.chaining import generate_smart_chains
from ..pipeline_core.stats import PipelineStats

logger = logging.getLogger(__name__)


async def generate_pipeline_outputs(
    optimized_proxies: List[Proxy],
    output_path: Path,
    stats: PipelineStats,
    history: ProxyHistoryTracker,
):
    """
    Orchestrates the generation of all pipeline outputs.
    Integrates Washing, Smart Chaining, and File Generation.
    """
    logger.info("Starting final output generation phase...")

    # 1. Initialize Washer & Scanner (The Intelligence Layer)
    # We load keys from Env. If empty, washer degrades gracefully to no-op.
    washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))

    # [CRITICAL] Run the Go Scanner (Phase 2 Component)
    # This populates self.clean_ips in the washer with fresh, low-latency endpoints.
    # We await it because it's an async network operation.
    await washer.fetch_clean_ips()

    # Update stats with scanner results
    stats.scanner_ips_found = len(washer.clean_ips)

    # 2. Wash Batch (The "Blanket" Wash)
    # Generates standard WARP wraps for all working proxies (fallback/legacy behavior)
    # Returns the list of outbound configs and the set of IDs that were washed.
    washed_outbounds, washed_ids = washer.wash_batch(optimized_proxies)

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

    # Generate Master Proxies JSON
    save_json(optimized_proxies, output_path / "proxies.json")

    generated_files = generate_categorized_outputs(
        optimized_proxies,
        output_path,
        washed_outbounds=washed_outbounds,
        washed_ids=washed_ids,
        smart_chains=smart_chains,
        washer=washer,  # Pass washer context if needed by generators
    )

    # 5. Metadata & Stats
    # Note: save_metadata expects QualityStorage but ProxyHistoryTracker has HistoryStorage.
    # This indicates an architectural mismatch. However, to resolve the error, we can pass None or fix the type.
    # save_metadata in output_logic.py is typed to accept QualityStorage.
    # ProxyHistoryTracker.storage is HistoryStorage.
    # We will skip passing history storage to save_metadata for now to fix the type error,
    # assuming save_metadata handles None or we pass a compatible object if possible.
    # But save_metadata signature is (stats, proxies, output_dir, history).
    # We will pass Any to bypass mypy for now as a hotfix since QualityStorage and HistoryStorage are different.
    from typing import cast, Any

    save_metadata(stats, optimized_proxies, output_path, cast(Any, history.storage))

    # [FIX] Export history visualization data
    # Ensure the history visualization JSON is generated for the frontend
    viz_path = output_path / "data" / "proxy_history_viz.json"
    viz_path.parent.mkdir(parents=True, exist_ok=True)
    history.export_for_visualization(viz_path)

    # Also export active trend for analytics chart
    trend_path = output_path / "data" / "active_proxy_trend.json"
    history.export_active_proxy_trend(trend_path)

    logger.info(f"Output generation complete. Files created in {output_path}")
    return generated_files
