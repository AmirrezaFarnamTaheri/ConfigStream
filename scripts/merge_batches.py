import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
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
from configstream.transport.polyglot import create_polyglot_image  # noqa: E402


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
    print("\n=== Step 0: Merging Test Caches ===")
    main_cache = TestResultCache(db_path=str(output_dir / "test_cache.json"))
    total_caches_merged = 0
    for batch_dir in batch_output_dirs:
        cache_file = batch_dir / "data" / "test_cache.json"
        if cache_file.exists():
            print(f"Merging cache from {batch_dir.name}...")
            shard_cache = TestResultCache(db_path=str(cache_file))
            main_cache.merge(shard_cache)
            total_caches_merged += 1

    if total_caches_merged > 0:
        main_cache.cleanup_expired()
        main_cache.save()
        print(
            f"✅ Merged {total_caches_merged} test caches. Final cache has {len(main_cache._cache)} entries."
        )
    else:
        print("No test caches found to merge.")

    # --- Merge Telemetry (Source Quality & Anomaly) ---
    print("\n=== Step 0.5: Merging Telemetry ===")
    main_sq = SourceQualityTracker(db_path=output_dir / "data" / "source_quality.db")
    main_anomaly = AnomalyDetector(db_path=output_dir / "data" / "anomaly.db")

    for batch_dir in batch_output_dirs:
        sq_db = batch_dir / "data" / "source_quality.db"
        anomaly_db = batch_dir / "data" / "anomaly.db"

        if sq_db.exists():
            main_sq.merge_from(sq_db)
        if anomaly_db.exists():
            main_anomaly.merge_from(anomaly_db)

    print("✅ Merged Telemetry Databases.")

    # Map to store: config -> (proxy, timestamp)
    # This ensures we keep the latest version of each proxy
    all_proxies_map = {}

    # First, collect all batches with their timestamps
    batches_with_timestamps = []

    for batch_dir in batch_output_dirs:
        if not batch_dir.exists():
            print(f"Info: Batch directory {batch_dir} not found. Skipping.")
            continue

        # Load metadata to get run timestamp
        metadata_file = batch_dir / "metadata.json"
        if not metadata_file.exists():
            print(
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
                print(
                    f"Warning: Could not parse metadata in {batch_dir}: {e}. Using fallback."
                )
                timestamp = batch_dir.stat().st_mtime

        batches_with_timestamps.append((batch_dir, timestamp))

    # Sort batches by timestamp (oldest first, so newest overwrites)
    batches_with_timestamps.sort(key=lambda x: x[1])

    print(
        f"Processing {len(batches_with_timestamps)} batches in chronological order..."
    )

    total_processed = 0
    for batch_dir, batch_timestamp in batches_with_timestamps:
        # Try proxies.json first (new format), then fallback to index.json (old format)
        proxies_file = batch_dir / "proxies.json"
        if not proxies_file.exists():
            proxies_file = batch_dir / "index.json"

        if not proxies_file.exists():
            print(
                f"Info: Neither proxies.json nor index.json found in {batch_dir}. Skipping."
            )
            continue

        with open(proxies_file, "r") as f:
            try:
                proxies_data = json.load(f)
                total_processed += len(proxies_data)
                for proxy_data in proxies_data:
                    proxy = Proxy(**proxy_data)

                    # LATEST-WINS logic: Always overwrite with newer data
                    # Since we process in chronological order, later batches overwrite earlier ones
                    all_proxies_map[proxy.config] = (proxy, batch_timestamp)

                print(
                    f"Processed {batch_dir.name}: {len(proxies_data)} proxies at {datetime.fromtimestamp(batch_timestamp).isoformat()}"
                )
            except (json.JSONDecodeError, TypeError) as e:
                print(
                    f"Warning: Could not process {proxies_file}. Error: {e}. Skipping."
                )

    # Extract proxies from the map (discard timestamps)
    merged_proxies = [proxy for proxy, _ in all_proxies_map.values()]

    duplicates_removed = total_processed - len(merged_proxies)
    print(f"\n✅ Merged {len(merged_proxies)} unique proxies (latest version of each)")
    print(f"Total proxies processed across all batches: {total_processed}")
    print(f"Duplicates removed (keeping latest): {duplicates_removed}")

    # Sort proxies by latency for consistent output
    merged_proxies.sort(key=lambda p: (p.latency is None, calculate_compound_score(p)))

    print("\n=== Step 1: Ranking and Renaming ===")
    # Rank and rename all proxies by protocol
    ranked_proxies = rank_and_rename_proxies(merged_proxies)
    print(f"Ranked {len(ranked_proxies)} proxies by protocol and latency")

    print("\n=== Step 2: Selecting Top Configs ===")
    # Select top 1000 configs (top 50 per protocol + fill from overall)
    chosen_proxies = select_top_configs(
        ranked_proxies, top_per_protocol=50, total_limit=1000
    )

    # Clear the existing output directory
    output_dir.mkdir(exist_ok=True)
    # Do not delete everything, we might want to keep some files, but generally clean start is good
    # Except we might lose some persistent data if we are not careful?
    # Actually, persistent data is in `data/`, which we just merged into.
    # So deleting output/*.* files is fine.
    for file_path in output_dir.glob("*.*"):
        if file_path.is_file():
            file_path.unlink()

    # --- Regenerate output files ---
    print("\n=== Step 3: Generating Output Files ===")

    # 1. proxies.json (main output file)
    with open(output_dir / "proxies.json", "w") as f:
        json.dump([asdict(p) for p in ranked_proxies], f, indent=2)
    print(f"✓ Generated proxies.json ({len(ranked_proxies)} proxies)")

    # 4. Individual protocol files (*.txt) - from ranked proxies
    proxies_by_protocol = defaultdict(list)
    for proxy in ranked_proxies:
        proxies_by_protocol[proxy.protocol].append(proxy.config)

    for protocol, configs in proxies_by_protocol.items():
        with open(output_dir / f"{protocol}.txt", "w") as f:
            f.write("\n".join(configs))
    print(f"✓ Generated protocol files ({len(proxies_by_protocol)} protocols)")

    # 5. Subscription files (all.txt, base64.txt - from all ranked)
    all_configs = [p.config for p in ranked_proxies]

    # Initialize Signer
    signing_key = os.environ.get("SIGNING_KEY")
    signer = None
    if signing_key:
        try:
            signer = Signer(private_key_hex=signing_key)
            print("🔐 Signing enabled.")
        except Exception as e:
            print(f"⚠️ Signing setup failed: {e}")

    if all_configs:
        with open(output_dir / "all.txt", "w") as f:
            f.write("\n".join(all_configs))
        print(f"✓ Generated all.txt ({len(all_configs)} configs)")

        base64_subscription_content = generate_base64_subscription(ranked_proxies)
        with open(output_dir / "base64.txt", "w") as f:
            f.write(base64_subscription_content)
        print("✓ Generated base64.txt")

        # 5a. Sign Subscriptions
        if signer:
            # Sign base64.txt content
            try:
                signed_b64 = signer.sign_subscription(base64_subscription_content)
                with open(output_dir / "base64.signed.json", "w") as f:
                    json.dump(signed_b64, f)
                print("✓ Generated base64.signed.json")
            except Exception as e:
                print(f"⚠️ Failed to sign base64: {e}")

    # 6. CHOSEN subset files (top 1000 configs)
    print("\n=== Generating CHOSEN Subset Files ===")
    chosen_dir = output_dir / "chosen"
    chosen_dir.mkdir(exist_ok=True)

    # chosen/proxies.json
    with open(chosen_dir / "proxies.json", "w") as f:
        json.dump([asdict(p) for p in chosen_proxies], f, indent=2)
    print(f"✓ Generated chosen/proxies.json ({len(chosen_proxies)} proxies)")

    # chosen/all.txt
    chosen_configs = [p.config for p in chosen_proxies]
    with open(chosen_dir / "all.txt", "w") as f:
        f.write("\n".join(chosen_configs))
    print(f"✓ Generated chosen/all.txt ({len(chosen_configs)} configs)")

    # chosen/base64.txt (subscription link for top 1000)
    chosen_base64 = generate_base64_subscription(chosen_proxies)
    with open(chosen_dir / "base64.txt", "w") as f:
        f.write(chosen_base64)
    print("✓ Generated chosen/base64.txt")

    # 9. Client Configs (Clash, SingBox, Adapters)

    # Clash
    clash_content = generate_clash_config(ranked_proxies)
    with open(output_dir / "clash.yaml", "w") as f:
        f.write(clash_content)
    print("✓ Generated clash.yaml")

    # Sing-box
    singbox_content = generate_singbox_config(ranked_proxies)
    with open(output_dir / "singbox.json", "w") as f:
        f.write(singbox_content)
    print("✓ Generated singbox.json")

    if signer:
        try:
            signed_singbox = signer.sign_subscription(singbox_content)
            with open(output_dir / "singbox.signed.json", "w") as f:
                json.dump(signed_singbox, f)
            print("✓ Generated singbox.signed.json")
        except Exception as e:
            print(f"⚠️ Failed to sign singbox: {e}")

    # Steganography: Create Polyglot Image (The Gallery)
    # We embed the singbox.json into a carrier image
    carrier_image = root_dir / "frontend/assets/images/background.png"
    # Fallback to creating a dummy image if not exists (for testing)
    if not carrier_image.exists():
        # Check if there is any png
        pngs = list((root_dir / "frontend/assets/images").glob("*.png"))
        if pngs:
            carrier_image = pngs[0]
        else:
            print("⚠️ No carrier image found for steganography. Skipping.")
            carrier_image = None

    if carrier_image:
        try:
            polyglot_path = output_dir / "gallery.png"
            create_polyglot_image(
                str(carrier_image),
                singbox_content,
                str(polyglot_path),
                password=os.environ.get("STEGO_PASSWORD")
                or "default_password_if_missing",
            )
            print("✓ Generated gallery.png (Steganography)")
        except Exception as e:
            print(f"⚠️ Failed to generate stego image: {e}")

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
        print("✓ Generated adapter configs (Surge, Shadowrocket, Loon, QX, SIP008)")
    except Exception as e:
        print(f"⚠️ Failed to generate adapter configs: {e}")

    # chosen/protocols (individual protocol files for chosen)
    chosen_by_protocol = defaultdict(list)
    for proxy in chosen_proxies:
        chosen_by_protocol[proxy.protocol].append(proxy.config)

    for protocol, configs in chosen_by_protocol.items():
        with open(chosen_dir / f"{protocol}.txt", "w") as f:
            f.write("\n".join(configs))
    print(f"✓ Generated {len(chosen_by_protocol)} chosen protocol files")

    # 7. statistics.json
    print("\n=== Generating Statistics ===")
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
    print("✓ Generated statistics.json")

    # 8. metadata.json
    # Use output.py's save_metadata for consistency (includes latency distribution)

    # We need to reconstruct 'stats' dict for save_metadata
    # It expects keys: working, fetched_lines, duration
    # We don't have exact fetched_lines or duration for the merged set easily,
    # but we can approximate or aggregate if we stored them.
    # For now, we'll pass what we have.

    meta_stats = {
        "working": working_proxies,
        "fetched_lines": total_processed,  # Approximation
        "duration": 0.0,  # Merging is fast, duration not tracked per se
    }

    # save_metadata writes both metadata.json and summary.json
    save_metadata(meta_stats, ranked_proxies, output_dir)
    print("✓ Generated metadata.json and summary.json via shared logic")

    # --- Copy Wiki Documentation ---
    print("\n=== Step 4: Copying Wiki Documentation ===")
    wiki_src = root_dir / "docs" / "wiki"
    wiki_dest = output_dir / "wiki"

    if wiki_src.exists():
        wiki_dest.mkdir(exist_ok=True)
        for md_file in wiki_src.glob("*.md"):
            # Atomic copy manually since shutil isn't imported and we want control
            dest_file = wiki_dest / md_file.name
            dest_file.write_text(md_file.read_text())
        print(f"✓ Copied {len(list(wiki_src.glob('*.md')))} wiki pages to output/wiki/")
    else:
        print(
            "⚠️ Warning: docs/wiki directory not found. Wiki pages will not be deployed."
        )

    print(f"\n{'=' * 60}")
    print(f"✅ Successfully merged and processed {len(merged_proxies)} unique proxies")
    print("✅ Ranked all proxies by protocol and latency")
    print(
        f"✅ Selected top {len(chosen_proxies)} configs (available at output/chosen/)"
    )
    print(f"{'=' * 60}\n")


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
