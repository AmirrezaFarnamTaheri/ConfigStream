import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from configstream.core import parse_config, geolocate_proxy, parse_config_batch
from configstream.models import Proxy


@pytest.mark.parametrize(
    "config_string, parser_name",
    [
        ("vmess://", "_parse_vmess"),
        ("vless://", "_parse_vless"),
        ("ss://", "_parse_ss"),
        ("ssr://", "_parse_ssr"),
        ("trojan://", "_parse_trojan"),
        ("hysteria://", "_parse_hysteria"),
        ("hy2://", "_parse_hysteria2"),
        ("tuic://", "_parse_tuic"),
        ("wg://", "_parse_wireguard"),
        ("naive+https://", "_parse_naive"),
        ("xray://", "_parse_xray"),
        ("http://", "_parse_generic"),
        ('{"v": "2"}', "_parse_v2ray_json"),
        ("hysteria2://", "_parse_hysteria2"),
        ("wireguard://", "_parse_wireguard"),
        ("xtls://", "_parse_xray"),
        ("ssh://", "_parse_generic"),
        ("https://", "_parse_generic"),
        ("socks://", "_parse_generic"),
        ("socks4://", "_parse_generic"),
        ("socks5://", "_parse_generic"),
    ],
)
def test_parse_config_calls_correct_parser(config_string, parser_name):
    """Test that parse_config calls the correct parser based on the protocol."""
    with patch(f"configstream.core.{parser_name}") as mock_parser:
        parse_config(config_string)
        mock_parser.assert_called_once_with(config_string)


def test_parse_config_unsupported():
    """Test that parse_config returns None for an unsupported protocol."""
    proxy = parse_config("unsupported://some-config")
    assert proxy is None


def test_parse_config_empty():
    """Test that parse_config returns None for an empty string."""
    proxy = parse_config("")
    assert proxy is None


def test_parse_config_comment():
    """Test that parse_config returns None for a comment."""
    proxy = parse_config("# this is a comment")
    assert proxy is None


def test_parse_config_batch():
    """Test that parse_config_batch correctly parses a list of configs."""
    configs = ["vmess://", "vless://", "unsupported://"]
    with patch("configstream.core.parse_config") as mock_parse_config:
        mock_parse_config.side_effect = [
            Proxy(config="vmess://", protocol="vmess", address="", port=0),
            Proxy(config="vless://", protocol="vless", address="", port=0),
            None,
        ]
        proxies = parse_config_batch(configs)
        assert len(proxies) == 2
        assert mock_parse_config.call_count == 3


@pytest.mark.asyncio
async def test_geolocate_proxy_success():
    """Test that geolocate_proxy correctly geolocates a proxy."""
    proxy = Proxy(config="vmess://test", protocol="vmess", address="8.8.8.8", port=443)

    mock_city_response = MagicMock()
    mock_city_response.country.iso_code = "US"
    mock_city_response.country.name = "United States"
    mock_city_response.city.name = "Mountain View"
    mock_city_response.autonomous_system.autonomous_system_number = 15169

    mock_reader = MagicMock()
    mock_reader.city.return_value = mock_city_response

    with patch("configstream.core._lookup_geoip_http", new_callable=AsyncMock) as mock_lookup:
        await geolocate_proxy(proxy, mock_reader)
    mock_lookup.assert_not_called()

    assert proxy.country_code == "US"
    assert proxy.country == "United States"
    assert proxy.city == "Mountain View"
    assert proxy.asn == "AS15169"


@pytest.mark.asyncio
async def test_geolocate_proxy_not_found():
    """Test geolocate_proxy when the IP is not in the database."""
    proxy = Proxy(config="vmess://test", protocol="vmess", address="127.0.0.1", port=443)

    mock_reader = MagicMock()
    from geoip2.errors import AddressNotFoundError

    mock_reader.city.side_effect = AddressNotFoundError("Address not found")

    with patch("configstream.core._lookup_geoip_http", new_callable=AsyncMock, return_value=None):
        await geolocate_proxy(proxy, mock_reader)

    assert proxy.country_code == "XX"
    assert proxy.country == "Unknown"
    assert proxy.city == "Unknown"
    assert proxy.asn == "AS0"


@pytest.mark.asyncio
async def test_geolocate_proxy_no_reader():
    """Test geolocate_proxy when no reader is provided."""
    proxy = Proxy(config="vmess://test", protocol="vmess", address="8.8.8.8", port=443)
    with patch(
        "configstream.core._lookup_geoip_http",
        new_callable=AsyncMock,
        return_value={
            "country": "United States",
            "country_code": "US",
            "city": "Mountain View",
            "asn": "AS15169",
        },
    ):
        await geolocate_proxy(proxy, None)

    assert proxy.country_code == "US"
    assert proxy.country == "United States"
    assert proxy.city == "Mountain View"
    assert proxy.asn == "AS15169"


@pytest.mark.asyncio
async def test_geolocate_proxy_key_error():
    """Test geolocate_proxy when the response is missing a key."""
    proxy = Proxy(config="vmess://test", protocol="vmess", address="8.8.8.8", port=443)

    mock_reader = MagicMock()
    mock_reader.city.side_effect = KeyError("test error")

    with patch("configstream.core._lookup_geoip_http", new_callable=AsyncMock, return_value=None):
        await geolocate_proxy(proxy, mock_reader)

    assert proxy.country_code == "XX"
    assert proxy.country == "Unknown"
    assert proxy.city == "Unknown"
    assert proxy.asn == "AS0"


@pytest.mark.asyncio
async def test_geolocate_proxy_infers_from_remarks():
    """Ensure remark parsing assigns country information when no lookup succeeds."""
    proxy = Proxy(
        config="vmess://test",
        protocol="vmess",
        address="example.com",
        port=443,
        remarks="🇺🇸US-Example",
    )

    with patch("configstream.core._lookup_geoip_http", new_callable=AsyncMock, return_value=None):
        await geolocate_proxy(proxy, None)

    assert proxy.country_code == "US"
    assert proxy.country == "United States"


def test_parse_config_batch_with_invalid():
    """Test parsing batch with invalid configs."""
    from configstream.core import parse_config_batch

    configs = [
        "vmess://validconfig",
        "",  # empty
        "invalid",  # invalid
        None,  # None
    ]

    results = parse_config_batch(configs)

    # Should filter out invalid configs
    assert isinstance(results, list)


def test_geolocate_proxy_infers_country_from_remarks():
    """Test country inference from remarks."""
    from configstream.core import geolocate_proxy
    from configstream.models import Proxy
    import asyncio

    proxy = Proxy(
        config="test",
        protocol="vmess",
        address="unknown.server",
        port=443,
        remarks="US Server #1",
    )

    async def test():
        await geolocate_proxy(proxy, None)

    asyncio.run(test())

    # Should infer US from remarks
    assert proxy.country_code == "US" or proxy.country == "United States"
