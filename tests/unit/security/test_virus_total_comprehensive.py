"""Comprehensive tests for VirusTotal security module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import time
from collections import OrderedDict

from configstream.security.virus_total import (
    scan_url,
    check_ip_reputation,
    _IP_CACHE,
    CACHE_TTL,
    CACHE_SIZE,
)


class MockResponse:
    """Mock aiohttp response."""

    def __init__(self, status, data):
        self.status = status
        self._data = data

    async def json(self):
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class TestScanURL:
    """Test cases for scan_url function."""

    @pytest.mark.asyncio
    async def test_scan_url_no_api_key(self, caplog):
        """Test scan_url when no API key is configured."""
        with patch("configstream.security.virus_total.VT_API_KEY", ""):
            result = await scan_url("https://example.com")

            assert result == {"malicious": 0}
            assert any("api key not found" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_scan_url_success_clean(self):
        """Test scanning a clean URL."""
        mock_response = MockResponse(
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 0,
                            "suspicious": 0,
                            "harmless": 50,
                        }
                    }
                }
            },
        )

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await scan_url("https://safe-site.com")

                assert result["malicious"] == 0

    @pytest.mark.asyncio
    async def test_scan_url_success_malicious(self):
        """Test scanning a malicious URL."""
        mock_response = MockResponse(
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 15,
                            "suspicious": 3,
                        }
                    }
                }
            },
        )

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await scan_url("https://malicious-site.com")

                assert result["malicious"] == 15

    @pytest.mark.asyncio
    async def test_scan_url_not_found(self):
        """Test scanning URL that's not in VT database (404)."""
        mock_response = MockResponse(404, {})

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await scan_url("https://unknown-site.com")

                assert result["malicious"] == 0

    @pytest.mark.asyncio
    async def test_scan_url_api_error(self, caplog):
        """Test scanning URL with API error response."""
        mock_response = MockResponse(403, {})

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await scan_url("https://example.com")

                assert result["malicious"] == 0
                assert any("api error" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_scan_url_invalid_response_data(self):
        """Test scanning URL with invalid (non-dict) response data."""
        mock_response = MockResponse(200, "not a dict")

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await scan_url("https://example.com")

                assert result["malicious"] == 0

    @pytest.mark.asyncio
    async def test_scan_url_missing_nested_data(self):
        """Test scanning URL with missing nested data fields."""
        mock_response = MockResponse(200, {"data": {}})

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await scan_url("https://example.com")

                assert result["malicious"] == 0

    @pytest.mark.asyncio
    async def test_scan_url_network_exception(self, caplog):
        """Test scanning URL with network exception."""
        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.side_effect = Exception("Network error")

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await scan_url("https://example.com")

                assert result["malicious"] == 0
                assert any("scan failed" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_scan_url_base64_encoding(self):
        """Test that URL is properly base64 encoded for API."""
        mock_response = MockResponse(200, {"data": {"attributes": {"last_analysis_stats": {"malicious": 0}}}})

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                await scan_url("https://test.com/path?query=value")

                # Verify get was called with proper URL
                call_args = mock_session.get.call_args
                assert "urls/" in call_args[0][0]


class TestCheckIPReputation:
    """Test cases for check_ip_reputation function."""

    def setup_method(self):
        """Clear cache before each test."""
        _IP_CACHE.clear()

    @pytest.mark.asyncio
    async def test_check_ip_no_api_key(self):
        """Test check_ip_reputation when no API key is configured."""
        with patch("configstream.security.virus_total.VT_API_KEY", ""):
            result = await check_ip_reputation("1.1.1.1")

            assert result == {"malicious": 0}

    @pytest.mark.asyncio
    async def test_check_ip_success_clean(self):
        """Test checking a clean IP address."""
        mock_response = MockResponse(
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 0,
                            "harmless": 80,
                        }
                    }
                }
            },
        )

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await check_ip_reputation("8.8.8.8")

                assert result["malicious"] == 0

    @pytest.mark.asyncio
    async def test_check_ip_success_malicious(self):
        """Test checking a malicious IP address."""
        mock_response = MockResponse(
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 25,
                        }
                    }
                }
            },
        )

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await check_ip_reputation("10.0.0.1")

                assert result["malicious"] == 25

    @pytest.mark.asyncio
    async def test_check_ip_cache_hit(self):
        """Test that cached IP results are returned without API call."""
        # Populate cache
        test_ip = "192.168.1.1"
        cached_result = {"malicious": 5}
        _IP_CACHE[test_ip] = (cached_result, time.time())

        with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
            with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
                result = await check_ip_reputation(test_ip)

                assert result == cached_result
                # Verify no API call was made
                mock_session_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_ip_cache_expired(self):
        """Test that expired cache entries are refreshed."""
        test_ip = "192.168.1.2"
        old_result = {"malicious": 5}
        # Set cache entry with expired timestamp
        _IP_CACHE[test_ip] = (old_result, time.time() - CACHE_TTL - 1)

        mock_response = MockResponse(
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 10,
                        }
                    }
                }
            },
        )

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await check_ip_reputation(test_ip)

                assert result["malicious"] == 10
                # Verify API was called since cache expired
                mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_ip_cache_lru_behavior(self):
        """Test that cache moves accessed items to end (LRU)."""
        test_ip = "192.168.1.3"
        _IP_CACHE[test_ip] = ({"malicious": 0}, time.time())
        _IP_CACHE["other_ip"] = ({"malicious": 0}, time.time())

        with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
            await check_ip_reputation(test_ip)

        # test_ip should be moved to end
        assert list(_IP_CACHE.keys())[-1] == test_ip

    @pytest.mark.asyncio
    async def test_check_ip_cache_size_limit(self):
        """Test that cache respects size limit."""
        mock_response = MockResponse(
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 0,
                        }
                    }
                }
            },
        )

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                # Fill cache beyond size limit
                for i in range(CACHE_SIZE + 5):
                    await check_ip_reputation(f"192.168.1.{i}")

                # Cache should not exceed size limit
                assert len(_IP_CACHE) <= CACHE_SIZE

    @pytest.mark.asyncio
    async def test_check_ip_invalid_response_data(self):
        """Test checking IP with invalid (non-dict) response data."""
        mock_response = MockResponse(200, ["not", "a", "dict"])

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await check_ip_reputation("1.2.3.4")

                assert result["malicious"] == 0

    @pytest.mark.asyncio
    async def test_check_ip_api_error(self, caplog):
        """Test checking IP with API error response."""
        mock_response = MockResponse(429, {})  # Rate limit error

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await check_ip_reputation("1.2.3.4")

                assert result["malicious"] == 0
                assert any("api error" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_check_ip_network_exception(self, caplog):
        """Test checking IP with network exception."""
        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.side_effect = Exception("Network timeout")

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await check_ip_reputation("1.2.3.4")

                assert result["malicious"] == 0
                assert any("check failed" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_check_ip_caches_result(self):
        """Test that successful IP check is cached."""
        test_ip = "10.20.30.40"

        mock_response = MockResponse(
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 3,
                        }
                    }
                }
            },
        )

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await check_ip_reputation(test_ip)

                assert result["malicious"] == 3
                # Verify result is cached
                assert test_ip in _IP_CACHE
                cached_result, _ = _IP_CACHE[test_ip]
                assert cached_result == result

    @pytest.mark.asyncio
    async def test_check_ip_missing_nested_data(self):
        """Test checking IP with missing nested data fields."""
        mock_response = MockResponse(200, {"data": {"attributes": {}}})

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                result = await check_ip_reputation("1.2.3.4")

                assert result["malicious"] == 0


class TestCacheManagement:
    """Test cases for cache management."""

    def setup_method(self):
        """Clear cache before each test."""
        _IP_CACHE.clear()

    def test_cache_constants(self):
        """Test that cache constants are defined correctly."""
        assert CACHE_TTL > 0
        assert CACHE_SIZE > 0
        assert isinstance(_IP_CACHE, OrderedDict)

    @pytest.mark.asyncio
    async def test_cache_eviction_fifo(self):
        """Test that cache evicts oldest entries first (FIFO)."""
        mock_response = MockResponse(
            200,
            {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 0,
                        }
                    }
                }
            },
        )

        first_ip = "192.168.0.1"
        _IP_CACHE[first_ip] = ({"malicious": 0}, time.time())

        with patch("configstream.security.virus_total.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch("configstream.security.virus_total.VT_API_KEY", "test_key"):
                # Fill cache to trigger eviction
                for i in range(2, CACHE_SIZE + 2):
                    await check_ip_reputation(f"192.168.0.{i}")

                # First IP should have been evicted
                assert first_ip not in _IP_CACHE
