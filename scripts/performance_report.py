#!/usr/bin/env python3
"""
Generate performance report for ConfigStream pipeline

This script runs your pipeline and generates detailed performance metrics,
helping you understand where time is spent and track improvements over time.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from configstream.pipeline import run_full_pipeline  # noqa: E402


async def main():
    # Load sources - check standard batch files if sources.txt is missing
    sources_file = Path("sources.txt")
    if not sources_file.exists():
        batch_files = sorted(list(Path("sources").glob("batch_*.txt")))
        if batch_files:
            sources_file = batch_files[0]
            print(f"ℹ️ sources.txt not found, using {sources_file} instead.")
        else:
            print("❌ No source files found in sources/ or sources.txt")
            return 1

    sources = [
        line.strip()
        for line in sources_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    print(f"🚀 Running pipeline with {len(sources)} sources from {sources_file}...")
    print("   Limiting to 100 proxies for performance testing\n")

    # Environment Isolation
    import os
    original_warp = os.environ.get("WARP_KEY_POOL")
    if original_warp is not None:
        del os.environ["WARP_KEY_POOL"]

    try:
        # Run pipeline
        result = await run_full_pipeline(
            sources=sources,
            output_dir="benchmark_output",
            max_proxies=100,
            max_workers=20,
            timeout=10,
        )
    finally:
        # Restore Environment
        if original_warp is not None:
            os.environ["WARP_KEY_POOL"] = original_warp

    # Extract metrics
    stats = result.stats
    stats_dict = stats.to_dict()

    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "success": result.success,
        "sources": len(sources),
        "stats": stats_dict,
        "performance": {
            "total_time_seconds": stats.duration,
            "proxies_per_second": (
                (stats.tested / stats.duration) if stats.duration > 0 else 0
            ),
        },
    }

    # Save report
    report_file = Path("performance_report.json")
    report_file.write_text(json.dumps(report, indent=2))

    # Print summary
    print("=" * 60)
    print("📊 PERFORMANCE REPORT")
    print("=" * 60)
    print(f"✅ Success: {report['success']}")
    print(f"📦 Sources processed: {len(sources)}")
    print(f"🔍 Configs fetched: {stats.fetched_lines}")
    print(f"🧪 Proxies tested: {stats.tested}")
    print(f"✨ Working proxies: {stats.working}")
    print()
    print("⏱️  TIMING:")
    print(f"   Total time: {report['performance']['total_time_seconds']:.2f}s")
    print()
    print(
        f"🚀 Throughput: {report['performance']['proxies_per_second']:.1f} proxies/sec"
    )
    print("=" * 60)
    print(f"\\n📄 Full report saved to: {report_file}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
