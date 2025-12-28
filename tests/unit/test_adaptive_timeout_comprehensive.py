import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from configstream.adaptive_timeout import AdaptiveTimeout


@pytest.mark.asyncio
async def test_adaptive_timeout_concurrent_record():
    at = AdaptiveTimeout(history_file=Path("dummy"))

    # Concurrent recording
    tasks = []
    for i in range(50):
        tasks.append(at.record("src", float(i)))

    await asyncio.gather(*tasks)

    assert len(at.latencies) == 50
    # Check if update ran safely
    assert at.current_timeout > 0


@pytest.mark.asyncio
async def test_adaptive_timeout_eviction():
    at = AdaptiveTimeout(history_file=Path("dummy"))

    # Fill with 1000 sources
    # Note: record is async
    for i in range(1005):
        await at.record(f"src{i}", 1.0)

    assert len(at.source_latencies) <= 1000
    assert "src0" not in at.source_latencies  # Oldest evicted


@pytest.mark.asyncio
async def test_adaptive_timeout_jitter_calculation():
    at = AdaptiveTimeout(history_file=Path("dummy"))

    await at.record("src1", 10.0)
    await at.record("src1", 12.0)

    jitter = await at.get_jitter("src1")
    assert jitter > 0

    jitter_empty = await at.get_jitter("src2")
    assert jitter_empty == 0.0


def test_load_history_malformed(tmp_path):
    p = tmp_path / "corrupt.json"
    p.write_text("{invalid_json")

    at = AdaptiveTimeout(history_file=p, initial=15.0)
    assert at.current_timeout == 15.0
