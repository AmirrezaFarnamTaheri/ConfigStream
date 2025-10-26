
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys
from dataclasses import asdict, is_dataclass

# Add src to python path to allow importing from configstream
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / 'src'))

try:
    from configstream.models import Proxy
    # This function is internal but is the most reliable way to generate links
    from configstream.output import _generate_subscription_links
except ImportError:
    print("Error: Could not import from 'src/configstream'. Ensure it is installed in editable mode.", file=sys.stderr)
    sys.exit(1)


def merge_batches():
    """
    Merges the outputs from the individual batch runs into a single, unified output.
    This script reads the index.json from each batch, deduplicates the proxies,
    and then regenerates all output files from the merged data.
    """
    output_dir = root_dir / 'output'
    batch_output_dirs = sorted(list(root_dir.glob('output_batch_*')))

    all_proxies_map = {}

    for batch_dir in batch_output_dirs:
        if not batch_dir.exists():
            print(f"Info: Batch directory {batch_dir} not found. Skipping.")
            continue

        index_file = batch_dir / 'index.json'
        if not index_file.exists():
            print(f"Info: index.json not found in {batch_dir}. Skipping.")
            continue

        with open(index_file, 'r') as f:
            try:
                proxies_data = json.load(f)
                for proxy_data in proxies_data:
                    proxy = Proxy(**proxy_data)
                    # Use the raw config as the key to handle duplicates across batches
                    if proxy.config not in all_proxies_map:
                        all_proxies_map[proxy.config] = proxy
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Warning: Could not process {index_file}. Error: {e}. Skipping.")

    merged_proxies = list(all_proxies_map.values())

    # Sort proxies by latency for consistent output
    merged_proxies.sort(key=lambda p: (p.latency_ms is not None, p.latency_ms))

    # Clear the existing output directory
    output_dir.mkdir(exist_ok=True)
    for f in output_dir.glob('*.*'):
        if f.is_file():
            f.unlink()

    # --- Regenerate output files ---

    # 1. index.json
    with open(output_dir / 'index.json', 'w') as f:
        json.dump([asdict(p) for p in merged_proxies], f, indent=2)

    # 2. Individual protocol files (*.txt)
    proxies_by_protocol = defaultdict(list)
    for proxy in merged_proxies:
        proxies_by_protocol[proxy.protocol].append(proxy.config)

    for protocol, configs in proxies_by_protocol.items():
        with open(output_dir / f'{protocol}.txt', 'w') as f:
            # Corrected newline bug
            f.write('\n'.join(configs))

    # 3. Subscription files (all.txt, base64.txt, etc.)
    all_configs = [p.config for p in merged_proxies]
    if all_configs:
        with open(output_dir / 'all.txt', 'w') as f:
            f.write('\n'.join(all_configs))

        base64_configs = _generate_subscription_links(merged_proxies)
        with open(output_dir / 'base64.txt', 'w') as f:
            f.write('\n'.join(base64_configs))

    # 4. statistics.json
    stats = {
        "total_proxies": len(merged_proxies),
        "proxies_by_protocol": {k: len(v) for k, v in proxies_by_protocol.items()},
        "proxies_by_country": {},
        "top_10_countries": [],
    }
    country_counts = defaultdict(int)
    for proxy in merged_proxies:
        country_counts[proxy.country] += 1

    if country_counts:
        stats["proxies_by_country"] = dict(sorted(country_counts.items()))
        stats["top_10_countries"] = sorted(country_counts.items(), key=lambda item: item[1], reverse=True)[:10]

    with open(output_dir / 'statistics.json', 'w') as f:
        json.dump(stats, f, indent=2)

    # 5. metadata.json
    metadata = {
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "total_proxies": len(merged_proxies)
    }

    with open(output_dir / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Successfully merged {len(merged_proxies)} unique proxies from all batches.")

if __name__ == "__main__":
    merge_batches()
