import logging
from configstream.parsers.base import extract_config_lines, is_plausible_proxy_config


def test_extract_config_lines_logging(caplog):
    caplog.set_level(logging.DEBUG)

    payload = """
    vmess://valid_config
    invalid_protocol://something
    http://github.com/sub
    """

    configs = extract_config_lines(payload)

    assert len(configs) == 1
    assert "vmess://valid_config" in configs

    # Check logs for drop reasons
    # Note: exact log message depends on implementation details, checking substrings
    assert "Dropping invalid config line" in caplog.text
    assert "Invalid protocol 'invalid_protocol'" in caplog.text
    # http://github.com is blocked
    assert (
        "Implausible format or blocked domain" in caplog.text
        or "Reason: Implausible" in caplog.text
    )


def test_blocked_domains():
    assert is_plausible_proxy_config("http://github.com/user/repo") is False
    assert (
        is_plausible_proxy_config("https://raw.githubusercontent.com/config") is False
    )
    assert is_plausible_proxy_config("vmess://valid") is True
