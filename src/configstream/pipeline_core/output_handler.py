from typing import List
from ..models import Proxy
from ..proxy_history import ProxyHistoryTracker
from ..output import generate_smart_chains, generate_categorized_outputs, save_metadata
from ..adapters import get_adapter
from ..intelligence.washer import ProxyWasher
from ..intelligence.vectors import generate_vectors
from ..output_generators import generate_base64_subscription
from ..serialize import serialize_proxy
from ..consolidation import select_top_configs
import json
import logging
import os

logger = logging.getLogger(__name__)


async def generate_pipeline_outputs(
    optimized_proxies: List[Proxy], output_path, stats, history: ProxyHistoryTracker
):
    """
    Handles all output generation logic:
    - Washing
    - Smart Chains
    - Standard Outputs (txt, json)
    - Metadata
    - Vectors
    - Adapters
    - Chosen 1000
    """
    logger.info(f"Generating outputs for {len(optimized_proxies)} proxies...")

    stats.final_count = len(optimized_proxies)

    # --- Intelligence Phase: Washing & Chaining (Centralized) ---
    washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))

    # Fetch Clean IPs before washing
    await washer.fetch_clean_ips()

    washed_outbounds, washed_ids = washer.wash_batch(optimized_proxies)

    smart_chains = generate_smart_chains(optimized_proxies)

    generated_files = generate_categorized_outputs(
        optimized_proxies,
        output_path,
        washed_outbounds=washed_outbounds,
        washed_ids=washed_ids,
        smart_chains=smart_chains,
    )

    # NEW: Generate Metadata for Frontend
    save_metadata(stats.to_dict(), optimized_proxies, output_path)

    # NEW: Generate Static Vectors for Client-Side Search
    generate_vectors(optimized_proxies, output_path)

    # New Adapters Exports
    try:
        # Pass washed_outbounds to adapters that support it (Surge)
        (output_path / "surge.conf").write_text(
            get_adapter("surge").export(optimized_proxies, washed_outbounds)
        )
        (output_path / "shadowrocket.txt").write_text(
            get_adapter("shadowrocket").export(optimized_proxies, washed_outbounds)
        )
        # Loon
        (output_path / "loon.conf").write_text(
            get_adapter("loon").export(optimized_proxies, washed_outbounds)
        )
        # Quantumult X
        (output_path / "quantumult.conf").write_text(
            get_adapter("qx").export(optimized_proxies, washed_outbounds)
        )
        # SIP008
        (output_path / "sip008.json").write_text(
            get_adapter("sip008").export(optimized_proxies, washed_outbounds)
        )
    except Exception as e:
        logger.error(f"Failed to export adapters: {e}")

    # Chosen 1000 Generation
    chosen_proxies = select_top_configs(
        optimized_proxies, top_per_protocol=50, total_limit=1000
    )
    chosen_dir = output_path / "chosen"
    chosen_dir.mkdir(exist_ok=True)

    (chosen_dir / "proxies.json").write_text(
        json.dumps(
            [serialize_proxy(p, history.get_history(p.id)) for p in chosen_proxies],
            indent=2,
        )
    )
    (chosen_dir / "base64.txt").write_text(generate_base64_subscription(chosen_proxies))

    return generated_files
