# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from configstream.pipeline.core import StandardPipeline
from configstream.anomaly import AnomalyDetector


@pytest.mark.asyncio
async def test_failure_mode_cooldown(tmp_path, monkeypatch):
    """
    Scenario: All sources are on cooldown.
    Pipeline should exit gracefully (or process 0 sources) without crashing.
    """
    # Use a direct URL to trigger remote fetch logic and should_fetch check
    sources = ["https://example.com/sub"]

    # Mock SourceQualityTracker to always return False for should_fetch
    # We patch the base class QualityStorage.get_source_state to return "dead".
    # This affects all SourceQualityTracker instances regardless of where they are imported.
    from configstream.quality.storage import QualityStorage

    def fake_get_state(self, url):
        # (status, last_checked, consecutive_failures, reliability_score, fetched, working)
        return ("dead", 0, 0, 0.0, 0, 0)

    monkeypatch.setattr(QualityStorage, "get_source_state", fake_get_state)

    # Mock Blocklist update to avoid network
    # Must be async because pipeline awaits this hook.
    async def fake_update():
        return None

    monkeypatch.setattr("configstream.pipeline.DEFAULT_BLOCKLIST.update", fake_update)

    result = await run_full_pipeline(
        sources=sources, output_dir=str(tmp_path / "out"), dry_run=True
    )

    # Should succeed but process 0 sources
    assert result.success is True
    # The stats should show 0 fetched if everything was on cooldown
    assert result.stats.fetched_sources == 0


@pytest.mark.asyncio
async def test_failure_mode_anomaly_db_crash(tmp_path, monkeypatch):
    """
    Scenario: Anomaly Detector DB interactions raise exceptions.
    Pipeline should fail-open and continue processing.
    """
    src_file = tmp_path / "sources.txt"
    src_file.write_text(
        "ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMC4wLjAuMDo4Mzgy#Test", encoding="utf-8"
    )

    # Remove re-import of AnomalyDetector to fix F811
    # from configstream.anomaly import AnomalyDetector

    # Patch current API method used by the pipeline.
    def raising_is_safe(self, url, count):
        raise RuntimeError("DB Connection Failed")

    monkeypatch.setattr(AnomalyDetector, "is_safe", raising_is_safe)

    # Mock SourceQualityTracker to allow fetch
    monkeypatch.setattr(
        "configstream.source_quality.SourceQualityTracker.should_fetch",
        lambda s, u: True,
    )

    # Mock network fetch
    from configstream.fetcher_worker import FetchResult

    async def fake_fetch(*args, **kwargs):
        return {
            "https://example.com/sub": FetchResult(
                success=True,
                source="https://example.com/sub",
                content="ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMC4wLjAuMDo4Mzgy#Test",
                status_code=200,
            )
        }

    monkeypatch.setattr("configstream.fetcher.fetch_multiple_sources", fake_fetch)

    # Mock Blocklist
    async def fake_update():
        return None

    monkeypatch.setattr("configstream.pipeline.DEFAULT_BLOCKLIST.update", fake_update)

    # Mock GeoIP
    from configstream.geoip import GeoData

    # Use async mock for GeoIP lookup and keyword arguments for GeoData
    async def fake_lookup(self, ip):
        return GeoData(country_code="US", country_name="United States", city="City")

    monkeypatch.setattr(
        "configstream.geoip.GeoIPResolver.lookup",
        fake_lookup,
    )

    result = await run_full_pipeline(
        sources=[str(src_file)], output_dir=str(tmp_path / "out"), dry_run=True
    )

    # Should succeed despite AnomalyDetector crash (Fail Open)
    assert result.success is True
    assert result.stats.fetched_sources >= 1


@pytest.mark.asyncio
async def test_failure_mode_vt_missing(tmp_path, monkeypatch):
    """
    Scenario: VirusTotal API Key is missing.
    Pipeline should log warning but proceed.
    """
    src_file = tmp_path / "sources.txt"
    src_file.write_text(
        "ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMC4wLjAuMDo4Mzgy#Test", encoding="utf-8"
    )

    # Ensure env var is missing
    monkeypatch.delenv("VT_API_KEY", raising=False)

    # Mock fetch/geoip/blocklist as usual
    # Must be async because pipeline awaits this hook.
    async def fake_update():
        return None

    monkeypatch.setattr("configstream.pipeline.DEFAULT_BLOCKLIST.update", fake_update)

    from configstream.fetcher_worker import FetchResult

    async def fake_fetch(*args, **kwargs):
        return {
            "https://example.com/sub": FetchResult(
                success=True,
                source="https://example.com/sub",
                content="ss://YWVzLTI1Ni1nY206cGFzc3dvcmRAMC4wLjAuMDo4Mzgy#Test",
                status_code=200,
            )
        }

    monkeypatch.setattr("configstream.fetcher.fetch_multiple_sources", fake_fetch)
    from configstream.geoip import GeoData

    # Use async mock for GeoIP lookup and keyword arguments for GeoData
    async def fake_lookup(self, ip):
        return GeoData(country_code="US", country_name="United States", city="City")

    monkeypatch.setattr(
        "configstream.geoip.GeoIPResolver.lookup",
        fake_lookup,
    )

    result = await run_full_pipeline(
        sources=[str(src_file)], output_dir=str(tmp_path / "out"), dry_run=True
    )

    assert result.success is True
