#!/usr/bin/env python3
"""
Generate performance report for ConfigStream pipeline

This script runs your pipeline and generates detailed performance metrics,
helping you understand where time is spent and track improvements over time.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from configstream.pipeline import run_full_pipeline  # noqa: E402


async def main():
    # Load sources
    sources_file = Path("sources.txt")
    if not sources_file.exists():
        print("❌ sources.txt not found")
        return 1

    sources = [
        line.strip()
        for line in sources_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    print(f"🚀 Running pipeline with {len(sources)} sources...")
    print("   Limiting to 100 proxies for performance testing\n")

    # Run pipeline
    result = await run_full_pipeline(
        sources=sources,
        output_dir="benchmark_output",
        max_proxies=100,
        max_workers=20,
        timeout=10,
    )

    # Extract metrics
    # PipelineResult objects have attributes, not .get() methods
    stats = result.stats
    # Metrics are not directly on PipelineResult/Stats usually,
    # but PipelineStats might be convertable or accessed.
    # The original code expected a dict.
    # stats is a PipelineStats object.

    # We need to map PipelineStats to the expected format or just dump it.
    stats_dict = stats.to_dict()

    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "success": result.success,
        "sources": len(sources),
        "stats": stats_dict,
        # Performance metrics might be missing if not in PipelineResult
        # The previous code assumed "metrics" key in result.
        # But run_full_pipeline returns PipelineResult(success, stats, output_files)
        # It seems performance metrics might need to be derived from stats.
        "performance": {
            "total_time_seconds": stats.duration,
            # granular metrics might not be available in PipelineResult directly unless we change it
            # For now, use 0 or available data
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
