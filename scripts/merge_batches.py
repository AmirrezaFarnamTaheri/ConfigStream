import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict

# Add src directory to path for imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "src"))

from configstream.models import Proxy  # noqa: E402
from configstream.output import generate_base64_subscription  # noqa: E402


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
    merged_proxies.sort(key=lambda p: (p.latency_ms is not None, p.latency_ms))

    # Clear the existing output directory
    output_dir.mkdir(exist_ok=True)
    for f in output_dir.glob("*.*"):
        if f.is_file():
            f.unlink()

    # --- Regenerate output files ---

    # 1. index.json (legacy format)
    with open(output_dir / "index.json", "w") as f:
        json.dump([asdict(p) for p in merged_proxies], f, indent=2)

    # 2. proxies.json (frontend expects this!)
    with open(output_dir / "proxies.json", "w") as f:
        json.dump([asdict(p) for p in merged_proxies], f, indent=2)

    # 3. full/all.json (fallback data for frontend)
    full_dir = output_dir / "full"
    full_dir.mkdir(exist_ok=True)
    with open(full_dir / "all.json", "w") as f:
        json.dump([asdict(p) for p in merged_proxies], f, indent=2)

    # 4. Individual protocol files (*.txt)
    proxies_by_protocol = defaultdict(list)
    for proxy in merged_proxies:
        proxies_by_protocol[proxy.protocol].append(proxy.config)

    for protocol, configs in proxies_by_protocol.items():
        with open(output_dir / f"{protocol}.txt", "w") as f:
            # Corrected newline bug
            f.write("\n".join(configs))

    # 5. Subscription files (all.txt, base64.txt, etc.)
    all_configs = [p.config for p in merged_proxies]
    if all_configs:
        with open(output_dir / "all.txt", "w") as f:
            f.write("\n".join(all_configs))

        base64_subscription_content = generate_base64_subscription(merged_proxies)
        with open(output_dir / "base64.txt", "w") as f:
            f.write(base64_subscription_content)

    # 6. statistics.json
    # Count working proxies
    working_proxies = sum(1 for p in merged_proxies if p.is_working)

    # Count proxies by country
    country_counts = defaultdict(int)
    for proxy in merged_proxies:
        country_counts[proxy.country] += 1

    # Count proxies by ASN
    asn_counts = defaultdict(int)
    for proxy in merged_proxies:
        if proxy.asn:
            asn_counts[proxy.asn] += 1

    stats = {
        # Fields for main page stats card
        "total_tested": len(merged_proxies),
        "total_working": working_proxies,

        # Fields for analytics page charts
        "protocols": {k: len(v) for k, v in proxies_by_protocol.items()},
        "countries": dict(sorted(country_counts.items())),
        "asns": dict(sorted(asn_counts.items())),

        # Legacy/compatibility fields (keep for backward compatibility)
        "total_proxies": len(merged_proxies),
        "proxies_by_protocol": {k: len(v) for k, v in proxies_by_protocol.items()},
        "proxies_by_country": dict(sorted(country_counts.items())),
        "top_10_countries": sorted(
            country_counts.items(), key=lambda item: item[1], reverse=True
        )[:10],
    }

    with open(output_dir / "statistics.json", "w") as f:
        json.dump(stats, f, indent=2)

    # 7. metadata.json
    metadata = {
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "total_proxies": len(merged_proxies),
    }

    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Successfully merged {len(merged_proxies)} unique proxies from all batches.")


if __name__ == "__main__":
    merge_batches()
