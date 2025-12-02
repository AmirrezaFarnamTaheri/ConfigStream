import logging
from pathlib import Path
from typing import List

from .setup_path import setup_python_path

setup_python_path()

from configstream.test_cache import TestResultCache
from configstream.source_quality import SourceQualityTracker
from configstream.anomaly import AnomalyDetector

logger = logging.getLogger(__name__)


def merge_telemetry(batch_dirs: List[Path], output_dir: Path):
    """Merges test caches and telemetry databases."""

    # --- Merge Test Caches ---
    logger.info("\n=== Step 0: Merging Test Caches ===")
    main_cache = TestResultCache(db_path=str(output_dir / "test_cache.json"))
    total_caches_merged = 0
    for batch_dir in batch_dirs:
        cache_file = batch_dir / "data" / "test_cache.json"
        if cache_file.exists():
            logger.info(f"Merging cache from {batch_dir.name}...")
            shard_cache = TestResultCache(db_path=str(cache_file))
            main_cache.merge(shard_cache)
            total_caches_merged += 1

    if total_caches_merged > 0:
        main_cache.cleanup_expired()
        main_cache.save()
        logger.info(
            f"✅ Merged {total_caches_merged} test caches. Final cache has {len(main_cache._cache)} entries."
        )
    else:
        logger.info("No test caches found to merge.")

    # --- Merge Telemetry (Source Quality & Anomaly) ---
    logger.info("\n=== Step 0.5: Merging Telemetry ===")
    main_sq = SourceQualityTracker(db_path=output_dir / "data" / "source_quality.db")
    main_anomaly = AnomalyDetector(db_path=output_dir / "data" / "anomaly.db")

    for batch_dir in batch_dirs:
        sq_db = batch_dir / "data" / "source_quality.db"
        anomaly_db = batch_dir / "data" / "anomaly.db"

        if sq_db.exists():
            main_sq.merge_from(sq_db)
        if anomaly_db.exists():
            main_anomaly.merge_from(anomaly_db)

    logger.info("✅ Merged Telemetry Databases.")
