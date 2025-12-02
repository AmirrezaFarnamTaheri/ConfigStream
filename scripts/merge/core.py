import logging
import sys
from pathlib import Path

from .setup_path import setup_python_path

root_dir = setup_python_path()

from configstream.consolidation import rank_and_rename_proxies, select_top_configs
from .telemetry import merge_telemetry
from .proxies import load_and_merge_proxies
from .generators import generate_outputs
from .logs import consolidate_logs

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

    # 4. Generate Files
    logger.info("\n=== Step 3: Generating Output Files ===")
    proxies_by_proto = generate_outputs(
        ranked_proxies, chosen_proxies, output_dir, total_processed, root_dir
    )

    # 5. Logs & Summary
    summary_lines = [
        f"Total Processed (Raw): {total_processed}",
        f"Merged Unique: {len(merged_proxies)}",
        f"Total Working: {sum(1 for p in ranked_proxies if p.is_working)}",
        f"Chosen Subset: {len(chosen_proxies)}",
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
