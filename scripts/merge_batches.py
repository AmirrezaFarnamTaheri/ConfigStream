import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict, replace
from typing import List

# Add src directory to path for imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from configstream.models import Proxy  # noqa: E402
from configstream.output import generate_base64_subscription  # noqa: E402


def get_country_flag(country_code: str) -> str:
    """Convert country code to flag emoji."""
    if not country_code or len(country_code) != 2 or country_code == "XX":
        return "🌍"
    try:
        # Convert to regional indicator symbols
        return "".join(chr(127397 + ord(c)) for c in country_code.upper())
    except (ValueError, TypeError):
        return "🌍"


def rank_and_rename_proxies(proxies: List[Proxy]) -> List[Proxy]:
    """
    Rank proxies by protocol based on latency and rename them.
    Format: PROTOCOL-RANK [COUNTRY_FLAG] ||| ORIGINAL_NAME
    """
    # Group proxies by protocol
    proxies_by_protocol = defaultdict(list)
    for proxy in proxies:
        proxies_by_protocol[proxy.protocol].append(proxy)

    # Sort each protocol group by latency (lower is better)
    ranked_proxies = []
    for protocol, protocol_proxies in proxies_by_protocol.items():
        # Sort by latency (None values go to end)
        protocol_proxies.sort(
            key=lambda p: (p.latency is None, p.latency if p.latency else float("inf"))
        )

        # Rename with rank
        for rank, proxy in enumerate(protocol_proxies, start=1):
            protocol_upper = protocol.upper()
            country_flag = get_country_flag(proxy.country_code)
            original_name = proxy.remarks or "Unnamed"

            # New remarks format: PROTOCOL-RANK [FLAG] ||| ORIGINAL_NAME
            new_remarks = f"{protocol_upper}-{rank} [{country_flag}] ||| {original_name}"

            # Truncate at 80 characters to avoid overly long names
            if len(new_remarks) > 80:
                new_remarks = new_remarks[:77] + "..."

            # Create updated proxy with new remarks
            updated_proxy = replace(proxy, remarks=new_remarks)
            ranked_proxies.append(updated_proxy)

    return ranked_proxies


def select_top_configs(
    ranked_proxies: List[Proxy], top_per_protocol: int = 50, total_limit: int = 1000
) -> List[Proxy]:
    """
    Select top configs: top N per protocol, then fill to total_limit from overall ranking.

    Args:
        ranked_proxies: List of ranked proxies
        top_per_protocol: Number of top configs to take from each protocol (default: 50)
        total_limit: Total number of configs to select (default: 1000)

    Returns:
        List of selected proxies
    """
    # Group by protocol
    proxies_by_protocol = defaultdict(list)
    for proxy in ranked_proxies:
        proxies_by_protocol[proxy.protocol].append(proxy)

    # Select top N from each protocol
    selected = []
    selected_configs = set()  # Track selected configs to avoid duplicates

    for protocol, protocol_proxies in proxies_by_protocol.items():
        # Take top N from this protocol
        top_n = protocol_proxies[:top_per_protocol]
        for proxy in top_n:
            if proxy.config not in selected_configs:
                selected.append(proxy)
                selected_configs.add(proxy.config)
        available_count = len(protocol_proxies)
        print(f"  Selected {len(top_n)} from {protocol} " f"(available: {available_count})")

    print(f"Total selected from per-protocol top {top_per_protocol}: {len(selected)}")

    # If we haven't reached the limit, fill from overall ranking
    if len(selected) < total_limit:
        # Sort all proxies by latency overall
        overall_ranked = sorted(
            ranked_proxies,
            key=lambda p: (p.latency is None, p.latency if p.latency else float("inf")),
        )

        # Fill the gap
        for proxy in overall_ranked:
            if len(selected) >= total_limit:
                break
            if proxy.config not in selected_configs:
                selected.append(proxy)
                selected_configs.add(proxy.config)

        print("Filled gap with additional configs from overall ranking")

    print(f"Total chosen configs: {len(selected)}")
    return selected


def merge_batches():
    """
    Merges the outputs from the individual batch runs into a single, unified output.
    This script reads the index.json from each batch, deduplicates the proxies,
    and then regenerates all output files from the merged data.
    """
    output_dir = root_dir / "output"
    batch_output_dirs = sorted(list(root_dir.glob("output_batch_*")))

    all_proxies_map = {}

    for batch_dir in batch_output_dirs:
        if not batch_dir.exists():
            print(f"Info: Batch directory {batch_dir} not found. Skipping.")
            continue

        # Try proxies.json first (new format), then fallback to index.json (old format)
        proxies_file = batch_dir / "proxies.json"
        if not proxies_file.exists():
            proxies_file = batch_dir / "index.json"

        if not proxies_file.exists():
            print(f"Info: Neither proxies.json nor index.json found in {batch_dir}. Skipping.")
            continue

        with open(proxies_file, "r") as f:
            try:
                proxies_data = json.load(f)
                for proxy_data in proxies_data:
                    proxy = Proxy(**proxy_data)
                    # Use the raw config as the key to handle duplicates across batches
                    if proxy.config not in all_proxies_map:
                        all_proxies_map[proxy.config] = proxy
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Warning: Could not process {proxies_file}. Error: {e}. Skipping.")

    merged_proxies = list(all_proxies_map.values())

    # Sort proxies by latency for consistent output
    merged_proxies.sort(key=lambda p: (p.latency is None, p.latency if p.latency else float("inf")))

    print("\n=== Step 1: Ranking and Renaming ===")
    # Rank and rename all proxies by protocol
    ranked_proxies = rank_and_rename_proxies(merged_proxies)
    print(f"Ranked {len(ranked_proxies)} proxies by protocol and latency")

    print("\n=== Step 2: Selecting Top Configs ===")
    # Select top 1000 configs (top 50 per protocol + fill from overall)
    chosen_proxies = select_top_configs(ranked_proxies, top_per_protocol=50, total_limit=1000)

    # Clear the existing output directory
    output_dir.mkdir(exist_ok=True)
    for f in output_dir.glob("*.*"):
        if f.is_file():
            f.unlink()

    # --- Regenerate output files ---
    print("\n=== Step 3: Generating Output Files ===")

    # 1. index.json (legacy format - all ranked proxies)
    with open(output_dir / "index.json", "w") as f:
        json.dump([asdict(p) for p in ranked_proxies], f, indent=2)
    print("✓ Generated index.json ({len(ranked_proxies)} proxies)")

    # 2. proxies.json (frontend expects this - all ranked proxies!)
    with open(output_dir / "proxies.json", "w") as f:
        json.dump([asdict(p) for p in ranked_proxies], f, indent=2)
    print("✓ Generated proxies.json ({len(ranked_proxies)} proxies)")

    # 3. full/all.json (fallback data for frontend - all ranked)
    full_dir = output_dir / "full"
    full_dir.mkdir(exist_ok=True)
    with open(full_dir / "all.json", "w") as f:
        json.dump([asdict(p) for p in ranked_proxies], f, indent=2)
    print("✓ Generated full/all.json ({len(ranked_proxies)} proxies)")

    # 4. Individual protocol files (*.txt) - from ranked proxies
    proxies_by_protocol = defaultdict(list)
    for proxy in ranked_proxies:
        proxies_by_protocol[proxy.protocol].append(proxy.config)

    for protocol, configs in proxies_by_protocol.items():
        with open(output_dir / f"{protocol}.txt", "w") as f:
            f.write("\n".join(configs))
    print("✓ Generated {len(proxies_by_protocol)} protocol files")

    # 5. Subscription files (all.txt, base64.txt - from all ranked)
    all_configs = [p.config for p in ranked_proxies]
    if all_configs:
        with open(output_dir / "all.txt", "w") as f:
            f.write("\n".join(all_configs))
        print("✓ Generated all.txt ({len(all_configs)} configs)")

        base64_subscription_content = generate_base64_subscription(ranked_proxies)
        with open(output_dir / "base64.txt", "w") as f:
            f.write(base64_subscription_content)
        print("✓ Generated base64.txt")

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
    country_counts = defaultdict(int)
    for proxy in ranked_proxies:
        country_counts[proxy.country] += 1

    # Count proxies by ASN
    asn_counts = defaultdict(int)
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
        "top_10_countries": sorted(country_counts.items(), key=lambda item: item[1], reverse=True)[
            :10
        ],
    }

    with open(output_dir / "statistics.json", "w") as f:
        json.dump(stats, f, indent=2)
    print("✓ Generated statistics.json")

    # 8. metadata.json
    metadata = {
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "total_proxies": len(ranked_proxies),
        "chosen_proxies": len(chosen_proxies),
    }

    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print("✓ Generated metadata.json")

    print(f"\n{'=' * 60}")
    print(f"✅ Successfully merged and processed {len(merged_proxies)} unique proxies")
    print("✅ Ranked all proxies by protocol and latency")
    print(f"✅ Selected top {len(chosen_proxies)} configs (available at output/chosen/)")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    merge_batches()
