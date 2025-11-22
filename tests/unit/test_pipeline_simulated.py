import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.pipeline import run_full_pipeline
from configstream.fetcher import FetchResult
from copy import deepcopy


# Simple Geo Data Class to avoid MagicMock JSON issues
class SimpleGeoData:
    def __init__(self, code="XX", country="Unknown", city="Unknown", asn="", org=""):
        self.country_code = code
        self.country = country
        self.city = city
        self.asn = asn
        self.org = org


@pytest.mark.asyncio
async def test_pipeline_simulated_run(tmp_path):
    """
    Simulates a full pipeline run with mocked components to ensure high coverage
    without actual network calls.
    """
    with (
        patch(
            "configstream.pipeline_stages.fetch_multiple_sources", new_callable=AsyncMock
        ) as mock_fetch,
        patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver") as mock_geoip_cls,
        patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),
        patch("configstream.pipeline.output.save_metadata") as _mock_save_meta,
        patch("configstream.pipeline.get_adapter") as mock_get_adapter,
        patch("configstream.pipeline.select_top_configs") as mock_select_top,
        patch("configstream.pipeline.SourceQualityTracker") as mock_quality_cls,
        patch("configstream.pipeline.ConcurrencyManager") as mock_cm,
    ):
        # Setup ConcurrencyManager
        mock_cm_instance = mock_cm.return_value
        mock_cm_instance.start_tuner = AsyncMock()
        mock_cm_instance.stop_tuner = AsyncMock()
        mock_cm_instance.record = AsyncMock()  # record() is now async
        mock_sem = MagicMock()
        mock_sem.__aenter__.return_value = None
        mock_sem.__aexit__.return_value = None
        mock_cm_instance.get_semaphore.return_value = mock_sem

        # Setup Quality Tracker
        mock_quality_instance = mock_quality_cls.return_value
        mock_quality_instance.should_fetch.return_value = True

        # Setup Mock Fetcher
        mock_fetch.return_value = {
            "http://source1.com": FetchResult(
                success=True,
                source="http://source1.com",
                content="ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.2.3.4:8388#TestProxy1\n"
                "vless://uuid@5.6.7.8:443?security=reality&sni=example.com&pbk=pub&sid=sid&type=tcp&flow=xtls-rprx-vision#TestProxy2",
                status_code=200,
                response_time=0.5,
            )
        }

        # Setup Mock Tester - Return REAL Proxy objects
        mock_tester_instance = mock_tester_cls.return_value

        # Mock go_tester.available to False to force python test loop
        mock_tester_instance.go_tester.available = False

        async def mock_test(proxy):
            p = deepcopy(proxy)

            if "TestProxy1" in p.remarks:
                p.is_working = True
                p.latency = 100.0
            else:
                p.is_working = False
                p.latency = None

            # Ensure fields are JSON serializable
            p.country_code = None
            p.resolved_ip = None
            return p

        mock_tester_instance.test = mock_test

        # Setup Mock GeoIP
        mock_geoip_instance = mock_geoip_cls.return_value
        mock_geoip_instance.lookup.return_value = SimpleGeoData(
            code="US", country="United States", city="New York", asn="AS12345", org="ISP Inc"
        )

        # Setup Output
        output_dir = tmp_path / "output"
        mock_adapter = MagicMock()
        mock_adapter.export.return_value = "mock_config"
        mock_get_adapter.return_value = mock_adapter
        mock_select_top.return_value = []

        # RUN
        result = await run_full_pipeline(
            sources=["http://source1.com"],
            output_dir=str(output_dir),
            max_workers=2,
            timeout=1,
            max_latency=None,
            country_filter=None,
        )

        assert result.success is True
        mock_fetch.assert_called()
        assert result.stats.fetched_sources == 1
        assert result.stats.parsed == 2
        assert result.stats.tested == 2
        assert result.stats.working == 1
        # Use _mock_save_meta to make flake8 happy
        _mock_save_meta.assert_called()


@pytest.mark.asyncio
async def test_pipeline_with_filters(tmp_path):
    """
    Test pipeline with country filter and min latency.
    """
    with (
        patch(
            "configstream.pipeline_stages.fetch_multiple_sources", new_callable=AsyncMock
        ) as mock_fetch,
        patch("configstream.pipeline.SingBoxTester") as mock_tester_cls,
        patch("configstream.pipeline.GeoIPResolver") as mock_geoip_cls,
        patch("configstream.pipeline.DEFAULT_BLOCKLIST.update", new_callable=AsyncMock),
        patch("configstream.pipeline.output.save_metadata"),
        patch("configstream.pipeline.get_adapter"),
        patch("configstream.pipeline.select_top_configs"),
        patch("configstream.pipeline.SourceQualityTracker") as mock_quality_cls,
        patch("configstream.pipeline.ConcurrencyManager") as mock_cm,
    ):
        mock_cm_instance = mock_cm.return_value
        mock_cm_instance.start_tuner = AsyncMock()
        mock_cm_instance.stop_tuner = AsyncMock()
        mock_cm_instance.record = AsyncMock()  # record() is now async
        mock_sem = MagicMock()
        mock_sem.__aenter__.return_value = None
        mock_sem.__aexit__.return_value = None
        mock_cm_instance.get_semaphore.return_value = mock_sem

        mock_quality_instance = mock_quality_cls.return_value
        mock_quality_instance.should_fetch.return_value = True

        mock_fetch.return_value = {
            "http://source1.com": FetchResult(
                success=True,
                source="http://source1.com",
                content="ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.2.3.4:8388#USProxy\n"
                "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@5.6.7.8:8388#DEProxy",
                status_code=200,
            )
        }

        mock_tester_instance = mock_tester_cls.return_value
        # Mock go_tester.available to False to force python test loop
        mock_tester_instance.go_tester.available = False

        async def mock_test(proxy):
            p = deepcopy(proxy)
            p.is_working = True
            if "USProxy" in p.remarks:
                p.latency = 50.0
            else:
                p.latency = 500.0
            p.country_code = None
            p.resolved_ip = None
            return p

        mock_tester_instance.test = mock_test

        mock_geoip_instance = mock_geoip_cls.return_value

        def mock_lookup(ip):
            if ip == "1.2.3.4":
                return SimpleGeoData(code="US")
            else:
                return SimpleGeoData(code="DE")

        mock_geoip_instance.lookup.side_effect = mock_lookup

        result = await run_full_pipeline(
            sources=["http://source1.com"],
            output_dir=str(tmp_path / "output"),
            country_filter="US",
            max_latency=200,
        )

        assert result.success is True
        mock_fetch.assert_called()
        assert result.stats.working == 1
