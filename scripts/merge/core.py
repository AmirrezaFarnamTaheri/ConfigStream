import logging
import sys
import os
import asyncio
from typing import Any, Dict, List

from .setup_path import setup_python_path

root_dir = setup_python_path()


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("configstream_merge.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def merge_batches(
    batch_dir_glob: str = "output_batch_*", output_dir_str: str = "output"
):
    """
    Merges the outputs from the individual batch runs into a single, unified output.
    """
    from configstream.consolidation import (
        rank_and_rename_proxies,
        select_top_configs,
    )
    from .telemetry import merge_telemetry
    from .proxies import load_and_merge_proxies
    from .generators import generate_outputs
    from .logs import consolidate_logs
    from configstream.intelligence.washer.core import ProxyWasher
    from configstream.intelligence.vectors import generate_vectors
    from configstream.proxy_history import ProxyHistoryTracker

    output_dir = root_dir / output_dir_str
    batch_dirs = sorted(list(root_dir.glob(batch_dir_glob)))

    # 1. Telemetry
    merge_telemetry(batch_dirs, output_dir)

    # 2. Proxies
    merged_proxies, total_processed = load_and_merge_proxies(batch_dirs)

    # 3. Rank & Select
    logger.info("\n=== Step 1: Ranking and Renaming ===")
    ranked_proxies = rank_and_rename_proxies(merged_proxies)
    logger.info(f"Ranked {len(ranked_proxies)} proxies")

    logger.info("\n=== Step 2: Selecting Top Configs ===")
    chosen_proxies = select_top_configs(
        ranked_proxies, top_per_protocol=50, total_limit=1000
    )

    # --- Feature: Proxy Washing ---
    washed_outbounds: List[Dict[str, Any]] = []
    total_washed_candidates = 0
    total_revived = 0
    warp_keys = os.environ.get("WARP_KEY_POOL")
    if warp_keys:
        logger.info("\n=== Step 2.5: Washing Proxies ===")
        try:
            washer = ProxyWasher(warp_keys)
            # Fetch clean IPs asynchronously
            asyncio.run(washer.fetch_clean_ips())

            # Identify "Dirty" candidates
            # We only wash proxies that are flagged as 'dirty_ip' or have security issues,
            # OR if we want to be aggressive, we wash everything that isn't explicitly clean.
            # User directive: "wash all dirties... not all proxies including workings".
            # So we filter for dirty indicators.
            dirty_proxies = [
                p
                for p in ranked_proxies
                if "dirty_ip" in p.tags
                or p.security_issues
                or (
                    p.country_code in ["IR", "CN", "RU"]
                )  # Geo-based assumption of dirtiness/blocking
            ]

            total_washed_candidates = len(dirty_proxies)
            logger.info(
                f"Identified {total_washed_candidates} dirty proxies for washing."
            )

            washed_outbounds, washed_ids = washer.wash_batch(dirty_proxies)
            logger.info(f"Generated {len(washed_outbounds)//2} washed chains")

            # --- Feature: Washer Retest ---
            # Retest the generated chains to ensure they actually work.
            from configstream.testers.go import GoBatchTester

            # Assuming we assume there is a Relay+Exit pair in sequence.
            # Group them into chains.
            chains_to_test = []
            if len(washed_outbounds) % 2 == 0:
                for i in range(0, len(washed_outbounds), 2):
                    relay = washed_outbounds[i]
                    exit_node = washed_outbounds[i + 1]
                    # The exit node tag is unique and sufficient ID
                    chain_id = exit_node.get("tag", f"chain_{i}")
                    chains_to_test.append(
                        {"id": chain_id, "outbounds": [relay, exit_node]}
                    )

                if chains_to_test:
                    logger.info(f"Retesting {len(chains_to_test)} washed chains...")
                    # Initialize tester (ensure binary path is correct)
                    tester = GoBatchTester(workers=50)
                    results = asyncio.run(tester.test_custom_configs(chains_to_test))

                    # Filter out failed chains
                    valid_washed_outbounds = []
                    passed_count = 0
                    for chain in chains_to_test:
                        cid = chain["id"]
                        if results.get(cid):
                            passed_count += 1
                            valid_washed_outbounds.extend(chain["outbounds"])
                        else:
                            logger.debug(f"Washed chain failed retest: {cid}")

                    total_revived = passed_count
                    logger.info(
                        f"Washer Retest Results: {passed_count}/{len(chains_to_test)} chains working."
                    )
                    washed_outbounds = valid_washed_outbounds
            else:
                logger.warning(
                    "Odd number of washed outbounds, skipping retest logic (integrity error)."
                )

        except Exception as e:
            logger.error(f"Failed to wash proxies: {e}")

    # --- Feature: Intelligence Vectors ---
    logger.info("\n=== Step 2.6: Generating Intelligence Vectors ===")
    try:
        generate_vectors(ranked_proxies, output_dir)
        logger.info("Vectors generated successfully.")
    except Exception as e:
        logger.error(f"Failed to generate vectors: {e}")

    # --- Feature: History Export ---
    logger.info("\n=== Step 2.7: Exporting History Visualization ===")
    try:
        history_file = output_dir / "data" / "proxy_history.json"
        if history_file.exists():
            history_tracker = ProxyHistoryTracker(history_path=history_file)
            history_tracker.export_for_visualization(
                output_dir / "data" / "proxy_history_viz.json"
            )
            history_tracker.export_active_proxy_trend(
                output_dir / "data" / "active_proxy_trend.json"
            )
            logger.info("History exported successfully.")
        else:
            logger.warning("No proxy history file found to export.")
    except Exception as e:
        logger.error(f"Failed to export history: {e}")

    # --- Feature: Smart Chains ---
    from configstream.intelligence.washer.chaining import generate_smart_chains

    # Use washer if available, otherwise just generate unwashed chains
    washer_instance = ProxyWasher(warp_keys) if warp_keys else None
    if washer_instance:
        # If we didn't fetch fetching clean IPs yet, do it if possible (though we did it above if keys exist)
        # Assuming washer_instance in local scope above is populated
        if (
            "washer" in locals() and washer
        ):  # reuse the one from Washing step if available
            washer_instance = washer

    smart_chains = generate_smart_chains(ranked_proxies, washer=washer_instance)

    # 4. Generate Files
    logger.info("\n=== Step 3: Generating Output Files ===")
    proxies_by_proto = generate_outputs(
        ranked_proxies,
        chosen_proxies,
        output_dir,
        total_processed,
        root_dir,
        washed_outbounds,
        smart_chains,
        total_washed_candidates,
        total_revived,
    )

    # 5. Logs & Summary
    summary_lines = [
        f"Total Processed (Raw): {total_processed}",
        f"Merged Unique: {len(merged_proxies)}",
        f"Total Working: {sum(1 for p in ranked_proxies if p.is_working)}",
        f"Chosen Subset: {len(chosen_proxies)}",
        f"Washed Chains: {len(washed_outbounds) // 2}",
        "",
        "Breakdown by Protocol (Working):",
    ]
    for proto, count in sorted(proxies_by_proto.items()):
        summary_lines.append(f"  - {proto}: {len(count)}")

    consolidate_logs(output_dir, summary_text="\n".join(summary_lines))

    logger.info(f"\n{'=' * 60}")
    logger.info(
        f"✅ Successfully merged and processed {len(merged_proxies)} unique proxies"
    )
    logger.info(f"{'=' * 60}\n")
