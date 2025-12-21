import logging
from configstream.parsers.base import extract_config_lines, is_plausible_proxy_config


def test_extract_config_lines_logging(caplog):
    caplog.set_level(logging.DEBUG)

    payload = """
    vmess://valid_config
    invalid_protocol://something
    http://github.com/sub
    """

    configs, stats = extract_config_lines(payload)

    assert len(configs) == 1
    assert "vmess://valid_config" in configs

    # Check stats presence instead of log messages for dropped lines
    assert "invalid_protocol" in stats
    assert "implausible_format" in stats

    # Verify summary log
    assert "Parsed 1 configs" in caplog.text


def test_blocked_domains():
    assert is_plausible_proxy_config("http://github.com/user/repo") is False
    assert (
        is_plausible_proxy_config("https://raw.githubusercontent.com/config") is False
    )
    assert is_plausible_proxy_config("vmess://valid") is True
