#!/usr/bin/env python3
"""Performance profiling helpers for ConfigStream."""

import asyncio
import cProfile
import io
import pstats
import sys
from pathlib import Path
from typing import Callable, Coroutine, Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from configstream import pipeline  # noqa: E402


def _run_coroutine(coro_factory: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
    """Run an async coroutine and return the result."""
    return asyncio.run(coro_factory())


def profile_pipeline(sources_file: str = "sources.txt", max_proxies: int = 100) -> pstats.Stats:
    """Profile the main pipeline execution."""

    async def _runner() -> Any:
        sources = Path(sources_file)
        if sources.exists():
            raw_sources = [
                line.strip()
                for line in sources.read_text().splitlines()
                if line.strip() and not line.startswith("#")
            ]
        else:
            raw_sources = []
        return await pipeline.run_full_pipeline(
            sources=raw_sources,
            output_dir=str(ROOT / "output"),
            max_proxies=max_proxies,
            timeout=10,
        )

    profiler = cProfile.Profile()
    profiler.enable()
    result = _run_coroutine(_runner)
    profiler.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(20)

    output = stream.getvalue()
    print("\nTop 20 cumulative functions:\n")
    print(output)

    report = ROOT / "performance_profile.txt"
    report.write_text(output)
    print(f"\nProfile saved to {report.relative_to(ROOT)}")
    print(f"Pipeline success: {result.get('success')}")
    print(f"Stats: {result.get('stats')}")

    metrics = result.get("metrics")
    if metrics:
        print("Performance metrics:")
        for key in (
            "total_seconds",
            "fetch_seconds",
            "parse_seconds",
            "test_seconds",
            "geo_seconds",
            "output_seconds",
            "proxies_tested",
            "proxies_working",
            "proxies_per_second",
        ):
            print(f"  {key}: {metrics.get(key)}")

    return stats


def main() -> None:
    profile_pipeline()


if __name__ == "__main__":
    main()
