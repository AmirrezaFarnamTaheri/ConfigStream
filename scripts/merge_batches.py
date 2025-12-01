import json
import os
import sys
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict

# Add src directory to path for imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from configstream.models import Proxy  # noqa: E402
from configstream.output_generators import (  # noqa: E402
    generate_base64_subscription,
    generate_singbox_config,
    generate_clash_config,
)
from configstream.output import save_metadata  # noqa: E402
from configstream.adapters import get_adapter  # noqa: E402
from configstream.test_cache import TestResultCache  # noqa: E402
from configstream.consolidation import (  # noqa: E402
    calculate_compound_score,
    rank_and_rename_proxies,
    select_top_configs,
)
from configstream.source_quality import SourceQualityTracker  # noqa: E402
from configstream.anomaly import AnomalyDetector  # noqa: E402
from configstream.crypto.signer import Signer  # noqa: E402
from configstream.transport.stego import generate_stego_assets  # noqa: E402
from configstream.output_transport import inject_stego_key_into_frontend  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
import shutil  # noqa: E402

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


def merge_batches(
    batch_dir_glob: str = "output_batch_*", output_dir_str: str = "output"
):
    """
    Merges the outputs from the individual batch runs into a single, unified output.

    This implements a STATEFUL, LATEST-WINS merge strategy:
    - Loads metadata.json from each batch to get run_timestamp
    - Processes batches in chronological order (oldest to newest)
    - For duplicate proxies (same config), keeps the LATEST version
    - This ensures no stale data and accurate proxy information
    """
    output_dir = root_dir / output_dir_str
    batch_output_dirs = sorted(list(root_dir.glob(batch_dir_glob)))

    # --- Merge Test Caches ---
    logger.info("\n=== Step 0: Merging Test Caches ===")
    main_cache = TestResultCache(db_path=str(output_dir / "test_cache.json"))
    total_caches_merged = 0
    for batch_dir in batch_output_dirs:
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

    for batch_dir in batch_output_dirs:
        sq_db = batch_dir / "data" / "source_quality.db"
        anomaly_db = batch_dir / "data" / "anomaly.db"

        if sq_db.exists():
            main_sq.merge_from(sq_db)
        if anomaly_db.exists():
            main_anomaly.merge_from(anomaly_db)

    logger.info("✅ Merged Telemetry Databases.")

    # Map to store: config -> (proxy, timestamp)
    # This ensures we keep the latest version of each proxy
    all_proxies_map = {}

    # First, collect all batches with their timestamps
    batches_with_timestamps = []

    for batch_dir in batch_output_dirs:
        if not batch_dir.exists():
            logger.info(f"Info: Batch directory {batch_dir} not found. Skipping.")
            continue

        # Load metadata to get run timestamp
        metadata_file = batch_dir / "metadata.json"
        if not metadata_file.exists():
            logger.warning(
                f"Warning: No metadata.json in {batch_dir}. Using directory mtime for ordering."
            )
            # Fallback: use directory modification time
            timestamp = batch_dir.stat().st_mtime
        else:
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
                    else:
                        timestamp = batch_dir.stat().st_mtime
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(
                    f"Warning: Could not parse metadata in {batch_dir}: {e}. Using fallback."
                )
                timestamp = batch_dir.stat().st_mtime

        batches_with_timestamps.append((batch_dir, timestamp))

    # Sort batches by timestamp (oldest first, so newest overwrites)
    batches_with_timestamps.sort(key=lambda x: x[1])

    logger.info(
        f"Processing {len(batches_with_timestamps)} batches in chronological order..."
    )

    total_processed = 0
    for batch_dir, batch_timestamp in batches_with_timestamps:
        # Try proxies.json first (new format), then fallback to index.json (old format)
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
                        # 0 latency usually indicates a failure or default value in some contexts.
                        # We treat it as None (failed/untested) to avoid sorting it as "fastest".
                        proxy_data["latency"] = None

                    proxy = Proxy(**proxy_data)

                    # LATEST-WINS logic: Always overwrite with newer data
                    # Since we process in chronological order, later batches overwrite earlier ones
                    # Use a robust key - config alone is good, but let's be sure.
                    all_proxies_map[proxy.config] = (proxy, batch_timestamp)

                logger.info(
                    f"Processed {batch_dir.name}: {len(proxies_data)} proxies at {datetime.fromtimestamp(batch_timestamp).isoformat()}"
                )
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(
                    f"Warning: Could not process {proxies_file}. Error: {e}. Skipping."
                )

    # Extract proxies from the map (discard timestamps)
    merged_proxies = [proxy for proxy, _ in all_proxies_map.values()]

    if not merged_proxies:
        logger.warning("⚠️ Warning: No proxies merged! Check input batch directories.")

    duplicates_removed = total_processed - len(merged_proxies)
    logger.info(
        f"\n✅ Merged {len(merged_proxies)} unique proxies (latest version of each)"
    )
    logger.info(f"Total proxies processed across all batches: {total_processed}")
    logger.info(f"Duplicates removed (keeping latest): {duplicates_removed}")

    # Sort proxies by latency for consistent output
    merged_proxies.sort(key=lambda p: (p.latency is None, calculate_compound_score(p)))

    logger.info("\n=== Step 1: Ranking and Renaming ===")
    # Rank and rename all proxies by protocol
    ranked_proxies = rank_and_rename_proxies(merged_proxies)
    logger.info(f"Ranked {len(ranked_proxies)} proxies by protocol and latency")

    logger.info("\n=== Step 2: Selecting Top Configs ===")
    # Select top 1000 configs (top 50 per protocol + fill from overall)
    chosen_proxies = select_top_configs(
        ranked_proxies, top_per_protocol=50, total_limit=1000
    )

    # Clear the existing output directory
    output_dir.mkdir(exist_ok=True)
    # Clean up old artifact files in the root of output directory.
    # We explicitly do NOT delete the 'data/' directory where persistent DBs live.
    for file_path in output_dir.glob("*.*"):
        if file_path.is_file():
            file_path.unlink()

    # --- Regenerate output files ---
    logger.info("\n=== Step 3: Generating Output Files ===")

    # 1. proxies.json (main output file)
    with open(output_dir / "proxies.json", "w") as f:
        json.dump([p.model_dump() for p in ranked_proxies], f, indent=2)
    logger.info(f"✓ Generated proxies.json ({len(ranked_proxies)} proxies)")

    # 4. Individual protocol files (*.txt) - from ranked proxies
    proxies_by_protocol = defaultdict(list)
    for proxy in ranked_proxies:
        proxies_by_protocol[proxy.protocol].append(proxy.config)

    for protocol, configs in proxies_by_protocol.items():
        with open(output_dir / f"{protocol}.txt", "w") as f:
            f.write("\n".join(configs))
    logger.info(f"✓ Generated protocol files ({len(proxies_by_protocol)} protocols)")

    # 5. Subscription files (all.txt, base64.txt - from all ranked)
    all_configs = [p.config for p in ranked_proxies]

    # Initialize Signer
    signing_key = os.environ.get("SIGNING_KEY")
    signer = None
    if signing_key:
        try:
            signer = Signer(private_key_hex=signing_key)
            logger.info("🔐 Signing enabled.")
        except Exception as e:
            logger.warning(f"⚠️ Signing setup failed: {e}")

    if all_configs:
        with open(output_dir / "all.txt", "w") as f:
            f.write("\n".join(all_configs))
        logger.info(f"✓ Generated all.txt ({len(all_configs)} configs)")

        base64_subscription_content = generate_base64_subscription(ranked_proxies)
        with open(output_dir / "base64.txt", "w") as f:
            f.write(base64_subscription_content)
        logger.info("✓ Generated base64.txt")

        # 5a. Sign Subscriptions
        if signer:
            # Sign base64.txt content
            try:
                signed_b64 = signer.sign_subscription(base64_subscription_content)
                with open(output_dir / "base64.signed.json", "w") as f:
                    json.dump(signed_b64, f)
                logger.info("✓ Generated base64.signed.json")
            except Exception as e:
                logger.warning(f"⚠️ Failed to sign base64: {e}")

    # 6. CHOSEN subset files (top 1000 configs)
    logger.info("\n=== Generating CHOSEN Subset Files ===")
    chosen_dir = output_dir / "chosen"
    chosen_dir.mkdir(exist_ok=True)

    # chosen/proxies.json
    with open(chosen_dir / "proxies.json", "w") as f:
        json.dump([p.model_dump() for p in chosen_proxies], f, indent=2)
    logger.info(f"✓ Generated chosen/proxies.json ({len(chosen_proxies)} proxies)")

    # chosen/all.txt
    chosen_configs = [p.config for p in chosen_proxies]
    with open(chosen_dir / "all.txt", "w") as f:
        f.write("\n".join(chosen_configs))
    logger.info(f"✓ Generated chosen/all.txt ({len(chosen_configs)} configs)")

    # chosen/base64.txt (subscription link for top 1000)
    chosen_base64 = generate_base64_subscription(chosen_proxies)
    with open(chosen_dir / "base64.txt", "w") as f:
        f.write(chosen_base64)
    logger.info("✓ Generated chosen/base64.txt")

    # 9. Client Configs (Clash, SingBox, Adapters)

    # Clash
    clash_content = generate_clash_config(ranked_proxies)
    with open(output_dir / "clash.yaml", "w") as f:
        f.write(clash_content)
    logger.info("✓ Generated clash.yaml")

    # Sing-box
    singbox_content = generate_singbox_config(ranked_proxies)
    with open(output_dir / "singbox.json", "w") as f:
        f.write(singbox_content)
    logger.info("✓ Generated singbox.json")

    if signer:
        try:
            signed_singbox = signer.sign_subscription(singbox_content)
            with open(output_dir / "singbox.signed.json", "w") as f:
                json.dump(signed_singbox, f)
            logger.info("✓ Generated singbox.signed.json")
        except Exception as e:
            logger.warning(f"⚠️ Failed to sign singbox: {e}")

    # Steganography: Marker-Based Approach (Primary)
    logger.info("\n=== Generating Steganography Assets ===")

    # 1. Copy frontend assets to output (if not already there)
    # This ensures stego.js is available for injection
    frontend_src = root_dir / "frontend"
    if frontend_src.exists():
        try:
            shutil.copytree(frontend_src, output_dir, dirs_exist_ok=True)
            logger.info(f"✓ Copied frontend assets to {output_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to copy frontend assets: {e}")

    # 2. Generate Key
    dynamic_key = os.environ.get("STEGO_KEY")
    if not dynamic_key:
        logger.info("ℹ️ STEGO_KEY not found in environment, generating a random one.")
        dynamic_key = Fernet.generate_key().decode()
    else:
        logger.info("ℹ️ Using STEGO_KEY from environment.")

    # 3. Generate Images
    assets_images = output_dir / "assets" / "images"
    if assets_images.exists():
        try:
            generate_stego_assets(
                config_dir=output_dir, assets_dir=assets_images, secret_key=dynamic_key
            )
            logger.info("✓ Generated stego assets (stealth_*.png)")
        except Exception as e:
            logger.warning(f"⚠️ Stego generation failed: {e}")
    else:
        logger.warning("⚠️ No assets/images found for steganography.")

    # 4. Inject Key
    js_path = output_dir / "assets" / "js" / "stego.js"
    if js_path.exists():
        try:
            inject_stego_key_into_frontend(dynamic_key, js_path)
            logger.info("✓ Injected dynamic key into stego.js")
        except Exception as e:
            logger.warning(f"⚠️ Failed to inject stego key: {e}")
    else:
        logger.warning("⚠️ stego.js not found for key injection.")

    # Adapters
    try:
        (output_dir / "surge.conf").write_text(
            get_adapter("surge").export(ranked_proxies)
        )
        (output_dir / "shadowrocket.txt").write_text(
            get_adapter("shadowrocket").export(ranked_proxies)
        )
        (output_dir / "loon.conf").write_text(
            get_adapter("loon").export(ranked_proxies)
        )
        (output_dir / "quantumult.conf").write_text(
            get_adapter("qx").export(ranked_proxies)
        )
        (output_dir / "sip008.json").write_text(
            get_adapter("sip008").export(ranked_proxies)
        )
        logger.info(
            "✓ Generated adapter configs (Surge, Shadowrocket, Loon, QX, SIP008)"
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to generate adapter configs: {e}")

    # chosen/protocols (individual protocol files for chosen)
    chosen_by_protocol = defaultdict(list)
    for proxy in chosen_proxies:
        chosen_by_protocol[proxy.protocol].append(proxy.config)

    for protocol, configs in chosen_by_protocol.items():
        with open(chosen_dir / f"{protocol}.txt", "w") as f:
            f.write("\n".join(configs))
    logger.info(f"✓ Generated {len(chosen_by_protocol)} chosen protocol files")

    # 7. statistics.json
    logger.info("\n=== Generating Statistics ===")
    # Count working proxies (from ranked list)
    working_proxies = sum(1 for p in ranked_proxies if p.is_working)
    working_chosen = sum(1 for p in chosen_proxies if p.is_working)

    # Count proxies by country
    country_counts: Dict[str, int] = defaultdict(int)
    for proxy in ranked_proxies:
        country_counts[proxy.country] += 1

    # Count proxies by ASN
    asn_counts: Dict[str, int] = defaultdict(int)
    for proxy in ranked_proxies:
        if proxy.asn:
            asn_counts[proxy.asn] += 1

    stats = {
        # Fields for main page stats card (all ranked proxies)
        "total_fetched": total_processed,
        "total_tested": len(ranked_proxies),
        "total_working": working_proxies,
        # Fields for analytics page charts
        "protocols": {k: len(v) for k, v in proxies_by_protocol.items()},
        "countries": dict(sorted(country_counts.items())),
        "asns": dict(sorted(asn_counts.items())),
        # Chosen subset stats
        "chosen": {
            "total": len(chosen_proxies),
            "working": working_chosen,
            "protocols": {k: len(v) for k, v in chosen_by_protocol.items()},
        },
        # Legacy/compatibility fields (keep for backward compatibility)
        "total_proxies": len(ranked_proxies),
        "proxies_by_protocol": {k: len(v) for k, v in proxies_by_protocol.items()},
        "proxies_by_country": dict(sorted(country_counts.items())),
        "top_10_countries": sorted(
            country_counts.items(), key=lambda item: item[1], reverse=True
        )[:10],
    }

    with open(output_dir / "statistics.json", "w") as f:
        json.dump(stats, f, indent=2)
    logger.info("✓ Generated statistics.json")

    # 8. metadata.json
    # Use output.py's save_metadata for consistency (includes latency distribution)

    # We reconstruct 'stats' dict for save_metadata using the aggregated totals.
    meta_stats = {
        "working": working_proxies,
        "fetched_lines": total_processed,
        "duration": 0.0,  # Merging duration is negligible for this context
    }

    # save_metadata writes both metadata.json and summary.json
    save_metadata(meta_stats, ranked_proxies, output_dir)
    logger.info("✓ Generated metadata.json and summary.json via shared logic")

    # 8. batch_statistics.json
    logger.info("\n=== Generating Batch Statistics ===")
    batch_stats: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "working": 0}
    )
    protocols_stats: defaultdict[str, defaultdict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for proxy in ranked_proxies:
        batch_source = proxy.batch_source or "unknown"
        batch_stats[batch_source]["total"] += 1
        if proxy.is_working:
            batch_stats[batch_source]["working"] += 1
        protocols_stats[batch_source][proxy.protocol] += 1

    final_batch_stats: dict[str, dict[str, object]] = {
        k: {
            "total": v["total"],
            "working": v["working"],
            "protocols": protocols_stats[k],
        }
        for k, v in batch_stats.items()
    }

    with open(output_dir / "batch_statistics.json", "w") as f:
        json.dump(final_batch_stats, f, indent=2)
    logger.info("✓ Generated batch_statistics.json")

    # --- Copy Wiki Documentation ---
    logger.info("\n=== Step 4: Copying Wiki Documentation ===")
    wiki_src = root_dir / "docs" / "wiki"
    wiki_dest = output_dir / "wiki"

    if wiki_src.exists():
        wiki_dest.mkdir(exist_ok=True)
        for md_file in wiki_src.glob("*.md"):
            # Atomic copy manually since shutil isn't imported and we want control
            dest_file = wiki_dest / md_file.name
            dest_file.write_text(md_file.read_text())
        logger.info(
            f"✓ Copied {len(list(wiki_src.glob('*.md')))} wiki pages to output/wiki/"
        )

        # Create wiki/index.html from frontend/wiki.html for /wiki support
        if (root_dir / "frontend/wiki.html").exists():
            (wiki_dest / "index.html").write_text(
                (root_dir / "frontend/wiki.html").read_text()
            )
            logger.info("✓ Created output/wiki/index.html")
    else:
        logger.warning(
            "⚠️ Warning: docs/wiki directory not found. Wiki pages will not be deployed."
        )

    # Create about/index.html for clean URL support
    about_dest = output_dir / "about"
    about_dest.mkdir(exist_ok=True)
    if (root_dir / "frontend/about.html").exists():
        (about_dest / "index.html").write_text(
            (root_dir / "frontend/about.html").read_text()
        )
        logger.info("✓ Created output/about/index.html")

    # Remove root about.html and wiki.html to prevent confusion and broken paths
    # (since they are now served from subdirectories with index.html)
    for filename in ["about.html", "wiki.html"]:
        p = output_dir / filename
        if p.exists():
            p.unlink()
            logger.info(f"✓ Removed redundant {filename} from output root")

    # --- Consolidate Logs ---

    # Construct Summary Text
    summary_lines = [
        f"Total Processed (Raw): {total_processed}",
        f"Merged Unique: {len(merged_proxies)}",
        f"Total Working: {working_proxies}",
        f"Chosen Subset: {len(chosen_proxies)} (Working: {working_chosen})",
        "",
        "Breakdown by Batch Source:",
    ]
    for src, data in final_batch_stats.items():
        summary_lines.append(f"  - {src}: {data['working']}/{data['total']} working")

    summary_lines.append("")
    summary_lines.append("Breakdown by Protocol (Working):")
    for proto, count in sorted(proxies_by_protocol.items()):
        summary_lines.append(f"  - {proto}: {len(count)}")

    consolidate_logs(output_dir, summary_text="\n".join(summary_lines))

    logger.info(f"\n{'=' * 60}")
    logger.info(
        f"✅ Successfully merged and processed {len(merged_proxies)} unique proxies"
    )
    logger.info("✅ Ranked all proxies by protocol and latency")
    logger.info(
        f"✅ Selected top {len(chosen_proxies)} configs (available at output/chosen/)"
    )
    logger.info(f"{'=' * 60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Merge batch outputs.")
    parser.add_argument(
        "--batch-glob",
        default="output_batch_*",
        help="Glob pattern for batch output directories",
    )
    parser.add_argument("--output-dir", default="output", help="Output directory")
    args = parser.parse_args()

    merge_batches(args.batch_glob, args.output_dir)
