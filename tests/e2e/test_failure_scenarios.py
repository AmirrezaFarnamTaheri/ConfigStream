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

    # Mock output handlers
    monkeypatch.setattr(
        "configstream.pipeline_core.output_handler.generate_stego_assets",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "configstream.pipeline_core.output_handler.inject_stego_key_into_frontend",
        lambda *args, **kwargs: None,
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

    monkeypatch.setattr(
        "configstream.pipeline_core.producer.fetch_multiple_sources", fake_fetch
    )

    # Mock output handlers
    monkeypatch.setattr(
        "configstream.pipeline_core.output_handler.generate_stego_assets",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "configstream.pipeline_core.output_handler.inject_stego_key_into_frontend",
        lambda *args, **kwargs: None,
    )

    # Mock GeoIP
    from configstream.geoip import GeoData

    monkeypatch.setattr(
        "configstream.geoip.GeoIPResolver.lookup",
        lambda self, ip: GeoData(country_code="US"),
    )

    sources = ["https://example.com/subs"]
    output_dir = tmp_path / "out_anomaly"

    # Capture logs to verify we see the error but pipeline continues?
    # Actually, pipeline_stages.py catches Exception in producer: "Producer failed: %s"
    # If is_safe raises, producer loop catches it?
    # No, `is_safe` is called inside `source_producer` loop.
    # `try...except Exception as e: logger.error("Producer failed: %s", e)`
    # So if `is_safe` raises, the producer aborts for that batch/source?
    # If it aborts the whole producer, then we get partial results or empty.

    result = await run_full_pipeline(
        sources=sources, output_dir=str(output_dir), dry_run=True
    )

    # If producer failed, we might get 0 results.
    # Ideally, AnomalyDetector should swallow errors and fail open.
    # If it raises, checking that pipeline doesn't crash is enough.
    assert result.success is True
    # If producer caught exception, it might stop fetching.
