import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from configstream.core import parse_config, parse_config_batch
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
        ("http://", "_parse_generic_url_scheme"),
        ('{"v": "2"}', "_parse_v2ray_json"),
        ("hysteria2://", "_parse_hysteria2"),
        ("wireguard://", "_parse_wireguard"),
        ("xtls://", "_parse_xray"),
        ("ssh://", "_parse_generic_url_scheme"),
        ("https://", "_parse_generic_url_scheme"),
        ("socks://", "_parse_generic_url_scheme"),
        ("socks4://", "_parse_generic_url_scheme"),
        ("socks5://", "_parse_generic_url_scheme"),
    ],
)
def test_parse_config_calls_correct_parser(config_string, parser_name):
    """Test that parse_config calls the correct parser based on the protocol."""
    with patch(f"configstream.parsers.{parser_name}") as mock_parser:
        # We need to reload the core module to ensure it picks up the patched parsers
        from importlib import reload
        from configstream import core

        reload(core)

        core.parse_config(config_string)
        mock_parser.assert_called_once_with(config_string)


def test_parse_config_unsupported_falls_back_to_auto_detect():
    """Test that an unsupported protocol falls back to auto-detection."""
    # This looks like a trojan link, and the auto-detector should pick it up
    # even though the scheme is "unsupported".
    proxy = parse_config("unsupported://some-config@example.com:443")
    assert proxy is not None
    assert proxy.protocol == "trojan"


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
