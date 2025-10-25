from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch


from configstream.logging_config import (
    ColoredFormatter,
    SensitiveDataFilter,
    _resolve_level,
    setup_logging,
)


# Test SensitiveDataFilter
def test_sensitive_data_filter_masks_credentials():
    """Test that credentials are masked."""
    filter_ = SensitiveDataFilter()
    record = logging.LogRecord(
        "test",
        logging.INFO,
        "/path/to/file.py",
        10,
        "User password = aabbccddeeff00112233445566778899",
        None,
        None,
    )
    filter_.filter(record)
    assert record.getMessage() == "User [MASKED_CREDENTIAL]"


def test_sensitive_data_filter_masks_email():
    """Test that email addresses are masked."""
    filter_ = SensitiveDataFilter()
    record = logging.LogRecord(
        "test",
        logging.INFO,
        "/path/to/file.py",
        10,
        "User email is test@example.com",
        None,
        None,
    )
    filter_.filter(record)
    assert record.getMessage() == "User email is [MASKED_EMAIL]"


# Test ColoredFormatter
@patch("sys.stdout.isatty", return_value=True)
def test_colored_formatter_adds_color_when_tty(mock_isatty):
    """Test that ANSI color codes are added when stdout is a TTY."""
    # The formatter needs a format string that includes the levelname
    formatter = ColoredFormatter("%(levelname)s - %(message)s")
    record = logging.LogRecord(
        "test", logging.INFO, "/path/to/file.py", 10, "Info message", (), None
    )
    formatted_message = formatter.format(record)
    assert "\033[32mINFO\033[0m" in formatted_message  # Green for INFO
    assert "Info message" in formatted_message


@patch("sys.stdout.isatty", return_value=False)
def test_colored_formatter_no_color_when_not_tty(mock_isatty):
    """Test that no ANSI color codes are added when stdout is not a TTY."""
    formatter = ColoredFormatter("%(levelname)s - %(message)s")
    record = logging.LogRecord(
        "test", logging.INFO, "/path/to/file.py", 10, "Info message", (), None
    )
    formatted_message = formatter.format(record)
    assert "\033[32m" not in formatted_message
    assert "INFO - Info message" in formatted_message


@patch("sys.stdout.isatty", return_value=True)
def test_colored_formatter_with_unspecified_level(mock_isatty):
    """Test that no color is added for a level not in the COLOURS map."""
    formatter = ColoredFormatter("%(levelname)s: %(message)s")
    # A custom level number not in the COLOURS map
    record = logging.LogRecord("test", 15, "/path/to/file.py", 10, "Custom level message", (), None)
    original_levelname = record.levelname
    formatted_message = formatter.format(record)
    # The levelname should not be modified with colors and should appear as is
    assert original_levelname in formatted_message
    assert "\033[" not in formatted_message


# Test _resolve_level
def test_resolve_level_returns_info_for_non_string_attribute():
    """Test that _resolve_level returns INFO if getattr finds a non-int."""
    # Create a mock logging module where 'FOO' is not an int
    mock_logging = MagicMock()
    mock_logging.FOO = "not-an-integer"
    with patch("configstream.logging_config.logging", mock_logging):
        # Assert against the mocked logging module's INFO attribute
        assert _resolve_level("FOO") == mock_logging.INFO


# Test setup_logging
@patch("configstream.logging_config.logging.getLogger")
def test_setup_logging_configures_root_logger(mock_get_logger, tmp_path):
    """Test that the root logger is configured correctly."""
    # More robust mocking to handle multiple getLogger calls
    loggers = {
        None: MagicMock(),
        "aiohttp": MagicMock(),
        "urllib3": MagicMock(),
        "asyncio": MagicMock(),
    }
    mock_get_logger.side_effect = lambda name=None: loggers[name]

    log_file = tmp_path / "test.log"
    setup_logging(level="DEBUG", log_file=log_file, format_style="simple")

    # Assertions on the root logger
    root_logger = loggers[None]
    mock_get_logger.assert_any_call()  # Called to get the root logger
    root_logger.setLevel.assert_called_with(logging.DEBUG)
    assert root_logger.addHandler.call_count == 2  # Console and file

    # Assertions on library loggers
    loggers["aiohttp"].setLevel.assert_called_with(logging.WARNING)
    loggers["urllib3"].setLevel.assert_called_with(logging.WARNING)
    loggers["asyncio"].setLevel.assert_called_with(logging.WARNING)


def test_setup_logging_handles_invalid_log_level():
    """Test that an invalid log level defaults to INFO."""
    loggers = {None: MagicMock()}
    with patch(
        "configstream.logging_config.logging.getLogger",
        side_effect=lambda name=None: loggers.setdefault(name, MagicMock()),
    ):
        setup_logging(level="INVALID_LEVEL", log_file=None)
        loggers[None].setLevel.assert_called_with(logging.INFO)
