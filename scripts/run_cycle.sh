#!/bin/bash
set -e

# 1. Run the pipeline (and capture logs)
echo "🚀 Starting Pipeline..."
# Loop through batches 1-10
for i in {1..10}; do
    echo "Running Batch $i..."
    # We use 'tee' to ensure the log file is saved for the analyzer
    python -m configstream.cli merge \
        --sources "sources/batch_$i.txt" \
        --output "output_batch_$i" \
        --max-workers 50 \
        | tee "pipeline_batch_$i.log"
done

# 2. Analyze and Refactor for NEXT time
echo "🔄 Analyzing performance and refactoring sources..."
python scripts/dynamic_reshard.py

echo "✅ Cycle complete. Sources optimized for next run."
