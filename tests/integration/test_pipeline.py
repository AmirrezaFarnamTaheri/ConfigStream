import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json
import base64
import aiohttp
import binascii
import logging

from configstream.pipeline import (
    run_full_pipeline,
    _normalise_source_url,
    _prepare_sources,
    _maybe_decode_base64,
    SourceValidationError,
    _fetch_source,
)
from configstream.models import Proxy


# Helper to create valid vmess configs for tests
def create_valid_vmess_config(ps: str, add: str = "test.com", country_code: str = "US") -> str:
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


@pytest.fixture(autouse=True)
def mock_geo_lookup():
    with patch(
        "configstream.core._lookup_geoip_http",
        new_callable=AsyncMock,
        return_value={
            "country": "United States",
            "country_code": "US",
            "city": "New York",
            "asn": "AS15169",
        },
    ) as mocked:
        yield mocked


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

    # ... (other tests for this class are fine)
    def test_url_with_scheme_but_no_netloc_raises_error(self):
        with pytest.raises(SourceValidationError, match="Source URL is missing a hostname"):
            _normalise_source_url("http:///no-hostname")


class TestPrepareSources:
    def test_unique_valid_sources(self):
        sources = ["http://a.com", "http://b.com", "local/file.txt"]
        assert _prepare_sources(sources) == sources

    # ... (other tests for this class are fine)
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


class TestMaybeDecodeBase64:
    def test_valid_base64_string(self):
        original = "hello\nworld"
        encoded = base64.b64encode(original.encode()).decode()
        assert _maybe_decode_base64(encoded) == original

    def test_plain_text_is_returned_as_is(self):
        assert _maybe_decode_base64("this is not base64") == "this is not base64"

    def test_multiline_payload_decoding_to_single_line_is_rejected(self):
        payload = "Zm9v\nZm9v\n"
        assert _maybe_decode_base64(payload) == payload

    def test_invalid_base64_characters(self):
        payload = "this is not valid base64!!"
        with pytest.raises(binascii.Error):
            base64.b64decode(payload, validate=True)  # Ensure it's actually invalid
        assert _maybe_decode_base64(payload) == payload

    def test_base64_decoding_to_invalid_utf8(self):
        invalid_utf8_bytes = b"\xff\xfe"
        encoded = base64.b64encode(invalid_utf8_bytes).decode()
        assert _maybe_decode_base64(encoded) == encoded


@pytest.mark.asyncio
class TestFetchSource:
    @patch("configstream.pipeline.get_client")
    async def test_fetch_source_no_usable_configs(self, mock_get_client):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "just some random text"
        mock_client.get.return_value = mock_response
        mock_get_client.return_value.__aenter__.return_value = mock_client

        configs, count = await _fetch_source(mock_client, "http://example.com/source")

        assert count == 0
        assert configs == []


@pytest.mark.asyncio
async def test_run_full_pipeline_success(mocker, tmp_path, no_pool_shutdown):
    config = create_valid_vmess_config("Canada-1")
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", config)],
    )
    mocker.patch("configstream.pipeline.geolocate_proxy", new_callable=AsyncMock)
    mocker.patch(
        "configstream.pipeline.SingBoxTester.test",
        new_callable=AsyncMock,
        return_value=Proxy(
            config=config, protocol="vmess", address="test.com", port=443, is_working=True
        ),
    )

    result = await run_full_pipeline(sources=["source.txt"], output_dir=str(tmp_path))
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

    result = await run_full_pipeline(sources=["source.txt"], output_dir=str(tmp_path))

    assert result["success"] is True
    assert result["stats"]["working"] == 0
    assert result["stats"]["tested"] == 1

    fallback_path = Path(result["output_files"]["full"])
    assert fallback_path.exists()
    fallback_payload = json.loads(fallback_path.read_text())
    assert len(fallback_payload) == result["stats"]["tested"]
    assert fallback_payload[0]["is_working"] is False
    assert result["error"] is None

    metadata = json.loads((tmp_path / "metadata.json").read_text())
    assert metadata["fallback_available"] is True
    assert metadata["tested_count"] == result["stats"]["tested"]
    assert result["error"] is None


@pytest.mark.asyncio
async def test_run_full_pipeline_max_proxies_limit(mocker, tmp_path, no_pool_shutdown):
    configs = "\n".join(
        [
            create_valid_vmess_config("p1"),
            create_valid_vmess_config("p2"),
            create_valid_vmess_config("p3"),
        ]
    )
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", configs)],
    )
    mocker.patch(
        "configstream.pipeline.SingBoxTester.test",
        new_callable=AsyncMock,
        side_effect=lambda p: Proxy(
            config=p.config, protocol=p.protocol, address=p.address, port=p.port, is_working=True
        ),
    )

    result = await run_full_pipeline(
        sources=["source.txt"], output_dir=str(tmp_path), max_proxies=2
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
            country_code="US",
        ),
        Proxy(
            config=create_valid_vmess_config("p2"),
            protocol="vmess",
            address="b.com",
            port=443,
            is_working=True,
            latency=800,
            country_code="CA",
        ),
        Proxy(
            config=create_valid_vmess_config("p3"),
            protocol="vmess",
            address="c.com",
            port=443,
            is_working=True,
            latency=1200,
            country_code="US",
        ),
    ]
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async", new_callable=AsyncMock, return_value=[]
    )  # no sources
    mocker.patch(
        "configstream.pipeline.SingBoxTester.test", new_callable=AsyncMock, side_effect=proxies
    )

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
    with patch("configstream.pipeline._fetch_source", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = ([config], 1)
        mocker.patch(
            "configstream.pipeline.SingBoxTester.test",
            new_callable=AsyncMock,
            return_value=Proxy(
                config=config, protocol="vmess", address="remote.com", port=443, is_working=True
            ),
        )

        result = await run_full_pipeline(
            sources=["http://remote.com/source"], output_dir=str(tmp_path)
        )

        assert result["success"] is True
        assert result["stats"]["fetched"] == 1
        assert result["stats"]["working"] == 1


@pytest.mark.asyncio
async def test_run_full_pipeline_remote_source_failure(mocker, tmp_path, caplog, no_pool_shutdown):
    """Test the pipeline completes but with 0 fetched when a remote source fails."""
    with patch("configstream.pipeline._fetch_source", new_callable=AsyncMock) as mock_fetch:
        # Simulate a fetch failure (e.g., timeout, HTTP 500)
        mock_fetch.side_effect = Exception("Fetch failed!")

        with caplog.at_level(logging.WARNING):
            result = await run_full_pipeline(
                sources=["http://failing-remote.com/source"], output_dir=str(tmp_path)
            )

            assert result["success"] is False
            assert "No configurations could be parsed" in result["error"]
            assert result["stats"]["fetched"] == 0
            assert "Failed to fetch http://failing-remote.com/source" in caplog.text


@pytest.mark.asyncio
async def test_run_full_pipeline_no_proxies_to_test_after_parsing(
    mocker, tmp_path, caplog, no_pool_shutdown
):
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", "invalid content")],
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
            config=config, protocol="vmess", address="test.com", port=443, is_working=True
        ),
    )
    mocker.patch("pathlib.Path.exists", return_value=False)

    await run_full_pipeline(sources=["source.txt"], output_dir=str(tmp_path))

    assert "GeoIP database not found" in caplog.text


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
    configs = "\n".join([create_valid_vmess_config(f"p{i}") for i in range(num_proxies)])
    mocker.patch(
        "configstream.pipeline.read_multiple_files_async",
        new_callable=AsyncMock,
        return_value=[("source.txt", configs)],
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
        result = await run_full_pipeline(sources=["source.txt"], output_dir=str(tmp_path))
        assert result["success"]
        assert result["stats"]["tested"] == num_proxies
        assert result["stats"]["working"] == num_proxies
        # Check for log messages indicating multiple batches
        assert "Testing batch 1/2" in caplog.text
        assert "Testing batch 2/2" in caplog.text
