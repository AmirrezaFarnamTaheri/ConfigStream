import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json
import base64
import binascii
import logging

from configstream.pipeline import (
    run_full_pipeline,
    _normalise_source_url,
    _prepare_sources,
    SourceValidationError,
)
from configstream.models import Proxy
from configstream.fetcher import FetchResult
from configstream.geoip_offline import GeoResult


# Helper to create valid vmess configs for tests
def create_valid_vmess_config(ps: str, add: str = "server.test", country_code: str = "US") -> str:
    """Creates a valid base64-encoded VMess config string."""
    config_dict = {
        "v": "2",
        "ps": ps,
        "add": add,
        "port": "443",
        "id": "a-uuid",
        "aid": "0",
        "net": "ws",
        "type": "none",
        "host": "",
        "path": "/",
        "tls": "",
    }
    json_config = json.dumps(config_dict)
    base64_config = base64.b64encode(json_config.encode()).decode()
    return f"vmess://{base64_config}"


@pytest.fixture
def mock_progress():
    """Fixture for a mock rich Progress object."""
    progress = MagicMock()
    progress.add_task = MagicMock(return_value=1)
    progress.update = MagicMock()
    return progress


class TestNormaliseSourceUrl:
    def test_valid_http_url(self):
        assert _normalise_source_url("http://example.com/source") == "http://example.com/source"

    def test_url_with_scheme_but_no_netloc_raises_error(self):
        with pytest.raises(SourceValidationError, match="Source URL is missing a hostname"):
            _normalise_source_url("http:///no-hostname")


class TestPrepareSources:
    def test_unique_valid_sources(self):
        sources = ["http://a.com", "http://b.com", "local/file.txt"]
        assert _prepare_sources(sources) == sources

    def test_empty_list_returns_empty_list(self):
        assert _prepare_sources([]) == []

    def test_duplicates_are_removed(self):
        sources = ["http://a.com", "http://a.com", "local/file.txt", "local/file.txt"]
        prepared = _prepare_sources(sources)
        assert len(prepared) == 2
        assert prepared.count("http://a.com") == 1
        assert prepared.count("local/file.txt") == 1

    def test_invalid_sources_are_filtered_with_warning(self, caplog):
        sources = ["http://valid.com", "ftp://invalid.com", ""]
        with caplog.at_level(logging.WARNING):
            prepared = _prepare_sources(sources)
            assert len(prepared) == 1
            assert "ftp://invalid.com" not in prepared
            assert "Skipping invalid source" in caplog.text


@pytest.mark.asyncio
async def test_run_full_pipeline_success(mocker, tmp_path, no_pool_shutdown):
    config = create_valid_vmess_config("Canada-1")

    async def mock_produce_raw_configs(sources, queue, *args, **kwargs):
        await queue.put(("source.txt", config))
        await queue.put(None)  # Sentinel
        return 1

    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", config)],
    )
    mocker.patch(
        "configstream.pipeline.SingBoxTester.test",
        new_callable=AsyncMock,
        return_value=Proxy(
            config=config, protocol="vmess", address="test.com", port=443, is_working=True
        ),
    )

    result = await run_full_pipeline(
        sources=["source.txt"], output_dir=str(tmp_path), leniency=True
    )
    assert result["success"] is True
    assert result["stats"]["fetched"] > 0
    assert result["stats"]["working"] > 0


@pytest.mark.asyncio
async def test_run_full_pipeline_no_sources_or_proxies(tmp_path, no_pool_shutdown):
    result = await run_full_pipeline(sources=[], output_dir=str(tmp_path))
    assert result["success"] is False
    assert "No sources provided" in result["error"]


@pytest.mark.asyncio
async def test_run_full_pipeline_no_working_proxies(mocker, tmp_path, no_pool_shutdown):
    config = create_valid_vmess_config("Failing-Proxy")

    # FIX: Mock read_multiple_files_async instead of _process_sources
    # This aligns with _produce_raw_configs calling read_multiple_files_async for local files
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", config)],
    )

    mocker.patch(
        "configstream.pipeline.SingBoxTester.test",
        new_callable=AsyncMock,
        return_value=Proxy(
            config=config, protocol="vmess", address="test.com", port=443, is_working=False
        ),
    )

    with patch("configstream.pipeline.FallbackManager.load_fallback", return_value=None):
        result = await run_full_pipeline(
            sources=["source.txt"], output_dir=str(tmp_path), leniency=True
        )

    assert result["success"] is True
    assert result["stats"]["working"] == 0
    assert result["stats"]["tested"] == 1

    # This should now pass because the pipeline actually processed the proxy
    # and triggered _write_outputs()
    fallback_path = Path(result["output_files"]["full"])
    assert fallback_path.exists()

    fallback_payload = json.loads(fallback_path.read_text())
    assert len(fallback_payload) == result["stats"]["tested"]
    assert fallback_payload[0]["is_working"] is False
    assert result["error"] is None

    metadata = json.loads((tmp_path / "metadata.json").read_text())
    assert metadata["working_count"] == 0
    assert metadata["stats"]["total_tested"] == result["stats"]["tested"]


@pytest.mark.asyncio
async def test_run_full_pipeline_max_proxies_limit(mocker, tmp_path, no_pool_shutdown):
    proxies = [
        Proxy(
            config=create_valid_vmess_config("p1", add="a.com"),
            protocol="vmess",
            address="a.com",
            port=443,
        ),
        Proxy(
            config=create_valid_vmess_config("p2", add="b.com"),
            protocol="vmess",
            address="b.com",
            port=443,
        ),
        Proxy(
            config=create_valid_vmess_config("p3", add="c.com"),
            protocol="vmess",
            address="c.com",
            port=443,
        ),
    ]
    proxy_configs = [p.config for p in proxies]
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", "\n".join(proxy_configs))],
    )
    mocker.patch(
        "configstream.pipeline.SingBoxTester.test",
        new_callable=AsyncMock,
        side_effect=lambda p: Proxy(
            config=p.config, protocol=p.protocol, address=p.address, port=p.port, is_working=True
        ),
    )

    result = await run_full_pipeline(
        sources=["source.txt"], output_dir=str(tmp_path), max_proxies=2, leniency=True
    )

    assert result["stats"]["tested"] == 2


@pytest.mark.asyncio
async def test_run_full_pipeline_with_filtering(mocker, tmp_path, no_pool_shutdown):
    proxies = [
        Proxy(
            config=create_valid_vmess_config("p1"),
            protocol="vmess",
            address="a.com",
            port=443,
            is_working=True,
            latency=100,
        ),
        Proxy(
            config=create_valid_vmess_config("p2"),
            protocol="vmess",
            address="b.com",
            port=443,
            is_working=True,
            latency=800,
        ),
        Proxy(
            config=create_valid_vmess_config("p3"),
            protocol="vmess",
            address="c.com",
            port=443,
            is_working=True,
            latency=1200,
        ),
    ]
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async", new_callable=AsyncMock, return_value=[]
    )  # no sources

    # Mock the tester to return the proxy as-is, preserving its attributes
    async def mock_tester_side_effect(proxy, *args, **kwargs):
        if proxy.address == "a.com":
            proxy.resolved_ip = "1.1.1.1"
        elif proxy.address == "b.com":
            proxy.resolved_ip = "2.2.2.2"
        else:
            proxy.resolved_ip = "3.3.3.3"
        return proxy

    mocker.patch(
        "configstream.pipeline.SingBoxTester.test",
        new_callable=AsyncMock,
        side_effect=mock_tester_side_effect,
    )

    def mock_lookup(ip):
        if ip == "1.1.1.1":
            return GeoResult(country_code="US")
        elif ip == "2.2.2.2":
            return GeoResult(country_code="CA")
        else:
            return GeoResult(country_code="US")

    mocker.patch("configstream.geoip_offline.DEFAULT_RESOLVER.lookup", side_effect=mock_lookup)

    result = await run_full_pipeline(
        sources=[],
        output_dir=str(tmp_path),
        proxies=proxies,
        country_filter="US",
        min_latency=50,
        max_latency=1000,
    )

    assert result["success"] is True
    assert result["stats"]["filtered"] == 1
    assert result["output_files"]


@pytest.mark.asyncio
async def test_run_full_pipeline_remote_source(mocker, tmp_path, no_pool_shutdown):
    config = create_valid_vmess_config("remote-1")
    mocker.patch(
        "configstream.fetcher.fetch_multiple_sources",
        new_callable=AsyncMock,
            return_value={"http://remote.com/source": FetchResult(source="http://remote.com/source", success=True, content=config)},
    )
    mocker.patch(
        "configstream.pipeline.SingBoxTester.test",
        new_callable=AsyncMock,
        return_value=Proxy(
            config=config, protocol="vmess", address="test.com", port=443, is_working=True
        ),
    )

    result = await run_full_pipeline(
        sources=["http://remote.com/source"], output_dir=str(tmp_path), leniency=True
    )

    assert result["success"] is True
    assert result["stats"]["fetched"] > 0
    assert result["stats"]["working"] == 1


@pytest.mark.asyncio
async def test_run_full_pipeline_remote_source_failure(mocker, tmp_path, caplog, no_pool_shutdown):
    """Test the pipeline completes but with 0 fetched when a remote source fails."""
    mocker.patch(
        "configstream.fetcher.fetch_multiple_sources",
        new_callable=AsyncMock,
        return_value={
                "http://failing-remote.com/source": FetchResult(source="http://failing-remote.com/source", success=False, error="timeout", content="")
        },
    )

    with caplog.at_level(logging.WARNING):
        result = await run_full_pipeline(
            sources=["http://failing-remote.com/source"], output_dir=str(tmp_path)
        )

        assert result["success"] is False
        assert "No configurations could be parsed" in result["error"]
        assert result["stats"]["fetched"] == 0


@pytest.mark.asyncio
async def test_run_full_pipeline_no_proxies_to_test_after_parsing(
    mocker, tmp_path, caplog, no_pool_shutdown
):
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[],
    )
    result = await run_full_pipeline(sources=["source.txt"], output_dir=str(tmp_path), proxies=[])
    assert not result["success"]
    assert "No configurations could be parsed" in result["error"]


@pytest.mark.asyncio
async def test_run_full_pipeline_no_proxies_to_test_no_sources(mocker, tmp_path, no_pool_shutdown):
    result = await run_full_pipeline(sources=[], output_dir=str(tmp_path), proxies=[])
    assert not result["success"]
    assert "No sources provided and no proxies supplied for retest" in result["error"]


@pytest.mark.asyncio
async def test_run_full_pipeline_geoip_db_not_found(mocker, tmp_path, caplog, no_pool_shutdown):
    import importlib
    from configstream import geoip_offline

    config = create_valid_vmess_config("p1")
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", config)],
    )
    mocker.patch(
        "configstream.pipeline.SingBoxTester.test",
        new_callable=AsyncMock,
        return_value=Proxy(
            config=config,
            protocol="vmess",
            address="test.com",
            port=443,
            is_working=True,
            resolved_ip="1.1.1.1",
        ),
    )
    mocker.patch("pathlib.Path.exists", return_value=False)

    # We need to reload the module because DEFAULT_RESOLVER is instantiated at the module level.
    # The mock needs to be in place before the resolver is created.
    importlib.reload(geoip_offline)

    with caplog.at_level(logging.WARNING):
        await run_full_pipeline(sources=["source.txt"], output_dir=str(tmp_path), leniency=True)

    assert "Offline GeoIP database not found" in caplog.text
    assert "ASN database not found" in caplog.text


@pytest.mark.asyncio
async def test_run_full_pipeline_all_proxies_filtered_by_security(
    mocker, tmp_path, caplog, no_pool_shutdown
):
    # Create a config that will be caught by the security validator (e.g., localhost)
    bad_config = create_valid_vmess_config("localhost-proxy", add="127.0.0.1")
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", bad_config)],
    )

    with caplog.at_level(logging.INFO):
        result = await run_full_pipeline(sources=["source.txt"], output_dir=str(tmp_path))
        assert not result["success"]
        assert "No configurations could be parsed or all were deemed insecure" in result["error"]
        assert "1 insecure proxies were filtered out" in caplog.text


@pytest.mark.asyncio
async def test_run_full_pipeline_multiple_batches(mocker, tmp_path, caplog, no_pool_shutdown):
    # Create more proxies than the batch size (1000)
    num_proxies = 1010
    proxies = [
        Proxy(
            config=create_valid_vmess_config(f"p{i}", add=f"server-{i}.test"),
            protocol="vmess",
            address=f"server-{i}.test",
            port=443,
        )
        for i in range(num_proxies)
    ]
    proxy_configs = [p.config for p in proxies]
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", "\n".join(proxy_configs))],
    )

    # Mock tester to return all as working
    mocker.patch(
        "configstream.pipeline.SingBoxTester.test",
        new_callable=AsyncMock,
        side_effect=lambda p: Proxy(
            config=p.config,
            protocol=p.protocol,
            address=p.address,
            port=p.port,
            is_working=True,
            latency=100,
        ),
    )

    with caplog.at_level(logging.INFO):
        result = await run_full_pipeline(
            sources=["source.txt"], output_dir=str(tmp_path), leniency=True
        )
        assert result["success"]
        assert result["stats"]["tested"] == num_proxies
        assert result["stats"]["working"] == num_proxies
        # Check for log messages indicating multiple batches
        assert "Testing batch 1/2" in caplog.text
        assert "Testing batch 2/2" in caplog.text
