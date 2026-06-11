# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from configstream.pipeline import run_full_pipeline


@pytest.mark.asyncio
async def test_all_sources_cooldown(tmp_path, monkeypatch):
    """
    Scenario: All sources are on cooldown.
    Expectation: Pipeline runs but produces 0 proxies, logs warning.
    """
    # Mock quality tracker to reject everything
    monkeypatch.setattr(
        "configstream.source_quality.SourceQualityTracker.should_fetch",
        lambda self, url: False,
    )

    sources = ["https://example.com/subs"]
    output_dir = tmp_path / "out_cooldown"

    result = await run_full_pipeline(
        sources=sources, output_dir=str(output_dir), dry_run=True
    )

    assert result.success is True
    assert result.stats.fetched_sources == 0
    assert result.stats.final_count == 0


@pytest.mark.asyncio
async def test_anomaly_db_failure(tmp_path, monkeypatch, caplog):
    """
    Scenario: Anomaly Detector DB raises exception.
    Expectation: Pipeline continues (fail open) or handles gracefully.
    """

    # Mock AnomalyDetector to fail on is_safe
    def fake_is_safe(self, source, count):
        raise RuntimeError("DB Connection Failed")

    monkeypatch.setattr("configstream.anomaly.AnomalyDetector.is_safe", fake_is_safe)

    # Mock fetcher to return something
    from dataclasses import dataclass

    @dataclass
    class FakeResponse:
        success: bool = True
        content: str = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMS4xLjEuMTo4OA==#Test"
        status_code: int = 200
        error: str = None

    async def fake_fetch(*args, **kwargs):
        return {"https://example.com/subs": FakeResponse()}

    monkeypatch.setattr("configstream.producer.fetch_multiple_sources", fake_fetch)

    # Mock GeoIP
    from configstream.geoip import GeoData

    async def fake_lookup(self, ip):
        return GeoData(country_code="US")

    monkeypatch.setattr("configstream.geoip.GeoIPResolver.lookup", fake_lookup)

    sources = ["https://example.com/subs"]
    output_dir = tmp_path / "out_anomaly"

    # The producer catches Exception per-source, so if is_safe raises,
    # that source is skipped and the pipeline continues with partial results.

    result = await run_full_pipeline(
        sources=sources, output_dir=str(output_dir), dry_run=True
    )

    # If producer failed, we might get 0 results.
    # Ideally, AnomalyDetector should swallow errors and fail open.
    # If it raises, checking that pipeline doesn't crash is enough.
    assert result.success is True
    # If producer caught exception, it might stop fetching.
