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
        sources=sources, output_dir="benchmark_output", max_proxies=100, max_workers=20, timeout=10
    )

    # Extract metrics
    metrics = result.get("metrics", {})
    stats = result.get("stats", {})

    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "success": result.get("success"),
        "sources": len(sources),
        "stats": stats,
        "performance": {
            "total_time_seconds": metrics.get("total_seconds", 0),
            "fetch_time_seconds": metrics.get("fetch_seconds", 0),
            "parse_time_seconds": metrics.get("parse_seconds", 0),
            "test_time_seconds": metrics.get("test_seconds", 0),
            "proxies_per_second": metrics.get("proxies_per_second", 0),
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
    print(f"🔍 Configs fetched: {stats.get('fetched', 0)}")
    print(f"🧪 Proxies tested: {stats.get('tested', 0)}")
    print(f"✨ Working proxies: {stats.get('working', 0)}")
    print()
    print("⏱️  TIMING:")
    print(f"   Total time: {report['performance']['total_time_seconds']:.2f}s")
    print(f"   Fetch time: {report['performance']['fetch_time_seconds']:.2f}s")
    print(f"   Parse time: {report['performance']['parse_time_seconds']:.2f}s")
    print(f"   Test time: {report['performance']['test_time_seconds']:.2f}s")
    print()
    print(f"🚀 Throughput: {report['performance']['proxies_per_second']:.1f} proxies/sec")
    print("=" * 60)
    print(f"\\n📄 Full report saved to: {report_file}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
