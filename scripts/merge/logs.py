import logging
import shutil
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

def consolidate_logs(output_dir: Path, summary_text: str = ""):
    """
    Finds all pipeline_batch_*.log files in the current directory (or restored artifacts),
    merges them into a single consolidated log file, and moves it to the output directory.
    Also includes the merge process log itself.
    """
    logger.info("=== Consolidating Pipeline Logs ===")

    # Force flush the current merge log so it's up to date on disk
    for handler in logging.getLogger().handlers:
        handler.flush()

    log_files = sorted(Path(".").glob("pipeline_batch_*.log"))

    # Add the merge log itself
    merge_log = Path("configstream_merge.log")
    if merge_log.exists():
        log_files.append(merge_log)

    if not log_files:
        logger.warning("No pipeline batch logs or merge logs found to consolidate.")
        return

    consolidated_log_path = output_dir / "consolidated_pipeline.log"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(consolidated_log_path, "w", encoding="utf-8") as outfile:
        outfile.write(f"Consolidated Pipeline Logs - {datetime.now().isoformat()}\n")
        outfile.write("=" * 60 + "\n")
        if summary_text:
            outfile.write("GLOBAL SUMMARY\n")
            outfile.write("-" * 20 + "\n")
            outfile.write(summary_text)
            outfile.write("\n" + ("=" * 60) + "\n\n")

        for log_file in log_files:
            logger.info(f"Merging {log_file.name}...")
            outfile.write(f"\n\n--- START OF {log_file.name} ---\n")
            try:
                with open(log_file, "r", encoding="utf-8", errors="replace") as infile:
                    shutil.copyfileobj(infile, outfile)
            except Exception as e:
                logger.error(f"Failed to read {log_file}: {e}")
                outfile.write(f"\n[ERROR READING FILE: {e}]\n")
            outfile.write(f"\n--- END OF {log_file.name} ---\n")

    logger.info(f"✅ Consolidated logs saved to {consolidated_log_path}")
