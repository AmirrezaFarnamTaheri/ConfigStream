#!/bin/bash
set -e

# ConfigStream Cycle Script
# Simulates the full CI/CD pipeline locally.

# 1. Run Batches (Sequential for local)
echo "🚀 Starting Pipeline..."
# Loop through batches 1-10 (or as many as exist)
for file in sources/batch_*.txt; do
    # Extract number from filename
    i=$(echo "$file" | sed 's/[^0-9]*//g')
    echo "Running Batch $i..."
    python -m configstream.cli merge \
        --sources "$file" \
        --output "output_batch_$i" \
        --max-workers 50 \
        | tee "pipeline_batch_$i.log"
done

# 2. Merge Batches
echo "🧩 Merging Batches..."
# Assuming WARP_KEY_POOL is set in env or .env
python -m scripts.merge_batches

# 3. Quality Gate
echo "🛡️ Running Healthcheck..."
python scripts/healthcheck.py --min-proxies 10 --min-success-rate 0.0

# 4. Analyze and Refactor for NEXT time
echo "🔄 Analyzing performance and refactoring sources..."
python scripts/dynamic_reshard.py

echo "✅ Cycle complete. Output in 'output/' directory."
