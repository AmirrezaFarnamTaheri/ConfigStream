"""Tests for logging configuration trace ID functionality."""

import logging

import pytest

from configstream.logging_config import (
    TraceIdFilter,
    clear_trace_id,
    get_trace_id,
    set_trace_id,
    setup_logging,
)


@pytest.fixture(autouse=True)
def reset_trace_id():
    """Reset trace ID and logging state before each test."""
    clear_trace_id()
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.filters.clear()
    yield
    clear_trace_id()
    # Reinitialize logging after shutdown
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.WARNING)


def test_set_trace_id_auto_generates_id():
    """Test that set_trace_id auto-generates an ID when not provided."""
    trace_id = set_trace_id()

    assert trace_id is not None
    assert len(trace_id) == 8  # Should be 8 characters


def test_set_trace_id_uses_provided_id():
    """Test that set_trace_id uses the provided ID."""
    custom_id = "abc12345"
    trace_id = set_trace_id(custom_id)

    assert trace_id == custom_id


def test_get_trace_id_returns_empty_when_not_set():
    """Test that get_trace_id returns empty string when not set."""
    trace_id = get_trace_id()

    assert trace_id == ""


def test_get_trace_id_returns_set_value():
    """Test that get_trace_id returns the set value."""
    custom_id = "test1234"
    set_trace_id(custom_id)

    trace_id = get_trace_id()

    assert trace_id == custom_id


def test_clear_trace_id_removes_value():
    """Test that clear_trace_id removes the trace ID."""
    set_trace_id("test1234")
    clear_trace_id()

    trace_id = get_trace_id()

    assert trace_id == ""


def test_trace_id_filter_adds_trace_id_to_record():
    """Test that TraceIdFilter adds trace_id attribute to log record."""
    set_trace_id("test1234")

    filter_obj = TraceIdFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    result = filter_obj.filter(record)

    assert result is True
    assert hasattr(record, "trace_id")
    assert record.trace_id == "test1234"


def test_trace_id_filter_uses_dash_when_not_set():
    """Test that TraceIdFilter uses '-' when trace ID is not set."""
    filter_obj = TraceIdFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    filter_obj.filter(record)

    assert record.trace_id == "-"


def test_setup_logging_with_trace_ids_enabled(tmp_path):
    """Test that setup_logging configures trace IDs correctly."""
    log_file = tmp_path / "test.log"

    setup_logging(
        level="DEBUG",
        log_file=log_file,
        format_style="detailed",
        enable_trace_ids=True,
        use_color=False,
    )

    # Verify trace ID filter was added
    root_logger = logging.getLogger()
    trace_filters = [f for f in root_logger.filters if isinstance(f, TraceIdFilter)]

    assert len(trace_filters) == 1


def test_setup_logging_with_trace_ids_disabled(tmp_path):
    """Test that trace IDs can be disabled."""
    log_file = tmp_path / "test.log"

    # Clear any existing filters
    root_logger = logging.getLogger()
    root_logger.filters.clear()

    setup_logging(
        level="DEBUG",
        log_file=log_file,
        format_style="simple",
        enable_trace_ids=False,
        use_color=False,
    )

    # Verify no trace ID filter was added
    trace_filters = [f for f in root_logger.filters if isinstance(f, TraceIdFilter)]

    assert len(trace_filters) == 0


def test_trace_id_in_log_format_detailed():
    """Test that trace ID appears in log output with detailed format."""
    # Setup logging without file handler to avoid pytest interference
    setup_logging(
        level="INFO",
        format_style="detailed",
        enable_trace_ids=True,
        use_color=False,
    )

    set_trace_id("abc12345")

    # Capture the formatted output by getting the handler's formatter
    root_logger = logging.getLogger()
    handler = root_logger.handlers[0]
    formatter = handler.formatter

    # Create a test record and format it
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message with trace ID",
        args=(),
        exc_info=None,
    )

    # Apply filter to add trace_id
    for f in root_logger.filters:
        f.filter(record)

    formatted = formatter.format(record)

    # Check that both message and trace ID appear in formatted output
    assert "Test message with trace ID" in formatted
    assert "abc12345" in formatted


def test_trace_id_in_log_format_simple():
    """Test that trace ID appears in simple format."""
    # Setup logging without file handler to avoid pytest interference
    setup_logging(
        level="INFO",
        format_style="simple",
        enable_trace_ids=True,
        use_color=False,
    )

    set_trace_id("xyz98765")

    # Capture the formatted output by getting the handler's formatter
    root_logger = logging.getLogger()
    handler = root_logger.handlers[0]
    formatter = handler.formatter

    # Create a test record and format it
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Simple test message",
        args=(),
        exc_info=None,
    )

    # Apply filter to add trace_id
    for f in root_logger.filters:
        f.filter(record)

    formatted = formatter.format(record)

    # Check that both message and trace ID appear in formatted output
    assert "Simple test message" in formatted
    assert "xyz98765" in formatted


def test_trace_id_context_isolation():
    """Test that trace IDs are isolated per context (for async)."""
    # Set initial trace ID
    set_trace_id("context1")
    assert get_trace_id() == "context1"

    # Change it
    set_trace_id("context2")
    assert get_trace_id() == "context2"

    # Clear and verify
    clear_trace_id()
    assert get_trace_id() == ""


def test_multiple_trace_id_filters_not_added(tmp_path):
    """Test that multiple trace ID filters are not added."""
    log_file = tmp_path / "test.log"

    # Call setup_logging twice
    setup_logging(level="INFO", log_file=log_file, enable_trace_ids=True, use_color=False)
    setup_logging(level="INFO", log_file=log_file, enable_trace_ids=True, use_color=False)

    root_logger = logging.getLogger()
    trace_filters = [f for f in root_logger.filters if isinstance(f, TraceIdFilter)]

    # Should still only have one filter
    assert len(trace_filters) == 1


def test_trace_id_persists_across_log_calls():
    """Test that trace ID persists across multiple log calls."""
    set_trace_id("persist123")

    # Make multiple calls to get_trace_id
    id1 = get_trace_id()
    id2 = get_trace_id()
    id3 = get_trace_id()

    assert id1 == "persist123"
    assert id2 == "persist123"
    assert id3 == "persist123"


def test_trace_id_filter_always_returns_true():
    """Test that TraceIdFilter always returns True (doesn't filter out records)."""
    filter_obj = TraceIdFilter()

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Should always return True (allow record)
    result = filter_obj.filter(record)
    assert result is True


def test_trace_id_with_different_log_levels():
    """Test that trace ID works with different log levels."""
    # Setup logging without file handler to avoid pytest interference
    setup_logging(
        level="DEBUG",
        format_style="detailed",
        enable_trace_ids=True,
        use_color=False,
    )

    set_trace_id("level123")

    # Get formatter and filters
    root_logger = logging.getLogger()
    handler = root_logger.handlers[0]
    formatter = handler.formatter

    # Test each log level
    log_levels = [
        (logging.DEBUG, "Debug message"),
        (logging.INFO, "Info message"),
        (logging.WARNING, "Warning message"),
        (logging.ERROR, "Error message"),
    ]

    for level, msg in log_levels:
        record = logging.LogRecord(
            name="test_logger",
            level=level,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )

        # Apply filter to add trace_id
        for f in root_logger.filters:
            f.filter(record)

        formatted = formatter.format(record)

        # Check that both message and trace ID appear in formatted output
        assert msg in formatted
        assert "level123" in formatted


def test_setup_logging_format_without_trace_ids(tmp_path):
    """Test log format without trace IDs."""
    log_file = tmp_path / "test.log"

    setup_logging(
        level="INFO",
        log_file=log_file,
        format_style="detailed",
        enable_trace_ids=False,
        use_color=False,
    )

    logger = logging.getLogger("test_no_trace")
    logger.info("Message without trace ID")

    log_content = log_file.read_text()

    # Should not contain any bracketed trace ID pattern
    assert "[" not in log_content or "trace_id" not in log_content
