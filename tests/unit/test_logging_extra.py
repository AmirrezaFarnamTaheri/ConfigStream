"""Tests for logging config."""

import logging

from configstream.logging_config import \
    SensitiveDataFilter  # Correct name based on file content
from configstream.logging_config import \
    setup_logging  # configure_uvicorn_logging # Not in file


def test_sensitive_filter():
    # Test filter directly
    f = SensitiveDataFilter()

    # Mask UUID
    record = logging.LogRecord(
        "name",
        logging.INFO,
        "path",
        1,
        "User uuid=12345678-1234-1234-1234-1234567890ab",
        (),
        None,
    )
    f.filter(record)
    assert "[MASKED_CREDENTIAL]" in record.msg
    assert "12345678" not in record.msg

    # Mask Email
    record = logging.LogRecord(
        "name", logging.INFO, "path", 1, "Contact user@example.com", (), None
    )
    f.filter(record)
    assert "[MASKED_EMAIL]" in record.msg
    assert "user@example.com" not in record.msg


def test_setup_logging_basic(tmp_path):
    log_file = tmp_path / "test.log"

    root = logging.getLogger()
    original_handlers = root.handlers[:]

    try:
        setup_logging(level="DEBUG", log_file=log_file)

        assert root.level == logging.DEBUG
        # Handlers: Console + File
        assert any(isinstance(h, logging.FileHandler) for h in root.handlers)

        # Log something
        logging.info("Test Message")

        # Verify file content
        for h in root.handlers:
            h.flush()
            h.close()  # Important to flush buffer

        if log_file.exists():
            content = log_file.read_text()
            assert "Test Message" in content

    finally:
        # Restore
        root.handlers = original_handlers


def test_setup_logging_json(tmp_path):
    json_log = tmp_path / "log.json"

    root = logging.getLogger()
    original_handlers = root.handlers[:]

    try:
        setup_logging(level="INFO", json_log_file=json_log, log_file=None)

        logging.info("JSON Msg")

        for h in root.handlers:
            h.flush()
            h.close()

        if json_log.exists():
            content = json_log.read_text()
            assert '"message": "JSON Msg"' in content
            assert '"level": "INFO"' in content

    finally:
        root.handlers = original_handlers


def test_setup_logging_no_file():
    setup_logging(log_file=None)
    # Should run without error
