# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for event_stream.py module.
Tests the EventStream class for real-time event emission.
"""

import json
from unittest.mock import patch
from configstream.event_stream import EventStream


class TestEventStream:
    """Test suite for EventStream class."""

    def test_init_with_path_object(self, tmp_path):
        """Test initialization with a Path object."""
        output_dir = tmp_path / "output"
        stream = EventStream(output_dir)
        assert stream.output_dir == output_dir

    def test_init_with_existing_directory(self, tmp_path):
        """Test initialization with an existing directory."""
        output_dir = tmp_path / "existing"
        output_dir.mkdir()
        stream = EventStream(output_dir)
        assert stream.output_dir == output_dir
        assert output_dir.exists()

    def test_init_with_nonexistent_directory(self, tmp_path):
        """Test initialization with a non-existent directory."""
        output_dir = tmp_path / "nonexistent"
        stream = EventStream(output_dir)
        # Should not create the directory at init time
        assert stream.output_dir == output_dir

    @patch("configstream.event_stream.logger")
    def test_emit_error_event(self, mock_logger, tmp_path):
        """Test emitting an error event."""
        stream = EventStream(tmp_path)
        stream.emit("error", "An error occurred")

        mock_logger.error.assert_called_once_with("[error] An error occurred")
        mock_logger.warning.assert_not_called()
        mock_logger.info.assert_not_called()

    @patch("configstream.event_stream.logger")
    def test_emit_critical_event(self, mock_logger, tmp_path):
        """Test emitting a critical event."""
        stream = EventStream(tmp_path)
        stream.emit("critical", "Critical failure")

        mock_logger.error.assert_called_once_with("[critical] Critical failure")
        mock_logger.warning.assert_not_called()
        mock_logger.info.assert_not_called()

    @patch("configstream.event_stream.logger")
    def test_emit_warning_event(self, mock_logger, tmp_path):
        """Test emitting a warning event."""
        stream = EventStream(tmp_path)
        stream.emit("warning", "Warning message")

        mock_logger.warning.assert_called_once_with("[warning] Warning message")
        mock_logger.error.assert_not_called()
        mock_logger.info.assert_not_called()

    @patch("configstream.event_stream.logger")
    def test_emit_info_event(self, mock_logger, tmp_path):
        """Test emitting an info event."""
        stream = EventStream(tmp_path)
        stream.emit("info", "Information message")

        mock_logger.info.assert_called_once_with("[info] Information message")
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()

    @patch("configstream.event_stream.logger")
    def test_emit_default_event_type(self, mock_logger, tmp_path):
        """Test emitting an event with unknown type defaults to info."""
        stream = EventStream(tmp_path)
        stream.emit("custom", "Custom event")

        mock_logger.info.assert_called_once_with("[custom] Custom event")
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()

    @patch("configstream.event_stream.logger")
    def test_emit_success_event(self, mock_logger, tmp_path):
        """Test emitting a success event (should use info)."""
        stream = EventStream(tmp_path)
        stream.emit("success", "Operation succeeded")

        mock_logger.info.assert_called_once_with("[success] Operation succeeded")

    @patch("configstream.event_stream.logger")
    def test_emit_empty_message(self, mock_logger, tmp_path):
        """Test emitting an event with an empty message."""
        stream = EventStream(tmp_path)
        stream.emit("info", "")

        mock_logger.info.assert_called_once_with("[info] ")

    @patch("configstream.event_stream.logger")
    def test_emit_multiline_message(self, mock_logger, tmp_path):
        """Test emitting an event with a multiline message."""
        stream = EventStream(tmp_path)
        message = "Line 1\nLine 2\nLine 3"
        stream.emit("info", message)

        mock_logger.info.assert_called_once_with(f"[info] {message}")

    @patch("configstream.event_stream.logger")
    def test_emit_message_with_special_characters(self, mock_logger, tmp_path):
        """Test emitting messages with special characters."""
        stream = EventStream(tmp_path)
        special_message = (
            "Error: Connection failed @ 192.168.1.1:8080 (timeout: 30s) - [CRITICAL]"
        )
        stream.emit("error", special_message)

        expected = special_message.replace("192.168.1.1", "[IP]")
        mock_logger.error.assert_called_once_with(f"[error] {expected}")

    @patch("configstream.event_stream.logger")
    def test_emit_message_with_unicode(self, mock_logger, tmp_path):
        """Test emitting messages with Unicode characters."""
        stream = EventStream(tmp_path)
        unicode_message = "Proxy connection: 成功 🎉 Ελληνικά ñ"
        stream.emit("info", unicode_message)

        mock_logger.info.assert_called_once_with(f"[info] {unicode_message}")

    @patch("configstream.event_stream.logger")
    def test_multiple_emit_calls(self, mock_logger, tmp_path):
        """Test multiple emit calls in sequence."""
        stream = EventStream(tmp_path)

        stream.emit("info", "First message")
        stream.emit("warning", "Second message")
        stream.emit("error", "Third message")

        assert mock_logger.info.call_count == 1
        assert mock_logger.warning.call_count == 1
        assert mock_logger.error.call_count == 1

    @patch("configstream.event_stream.logger")
    def test_emit_very_long_message(self, mock_logger, tmp_path):
        """Test emitting a very long message."""
        stream = EventStream(tmp_path)
        long_message = "X" * 10000
        stream.emit("info", long_message)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "[BASE64]" in call_args
        assert long_message not in call_args

    @patch("configstream.event_stream.logger")
    def test_emit_with_format_strings(self, mock_logger, tmp_path):
        """Test emitting messages with format string-like content."""
        stream = EventStream(tmp_path)
        message = "Value: %s, Count: %d, Percent: %.2f%%"
        stream.emit("info", message)

        mock_logger.info.assert_called_once_with(f"[info] {message}")

    @patch("configstream.event_stream.logger")
    def test_case_sensitive_event_types(self, mock_logger, tmp_path):
        """Test that event types are case-sensitive."""
        stream = EventStream(tmp_path)

        # Lowercase 'error' should trigger error log
        stream.emit("error", "lowercase error")
        mock_logger.error.assert_called_once()

        mock_logger.reset_mock()

        # Uppercase 'ERROR' should trigger info log (not in the if conditions)
        stream.emit("ERROR", "uppercase ERROR")
        mock_logger.info.assert_called_once()
        mock_logger.error.assert_not_called()

    @patch("configstream.event_stream.logger")
    def test_emit_with_numeric_message(self, mock_logger, tmp_path):
        """Test emitting with numeric content in message."""
        stream = EventStream(tmp_path)
        stream.emit("info", "Port: 8080, Timeout: 30, Success: 100%")

        mock_logger.info.assert_called_once()

    @patch("configstream.event_stream.logger")
    def test_emit_rapid_fire(self, mock_logger, tmp_path):
        """Test rapid consecutive emit calls."""
        stream = EventStream(tmp_path)

        for i in range(100):
            stream.emit("info", f"Message {i}")

        assert mock_logger.info.call_count == 100

    @patch("configstream.event_stream.logger")
    def test_emit_different_event_types_mixed(self, mock_logger, tmp_path):
        """Test emitting different event types in mixed order."""
        stream = EventStream(tmp_path)

        stream.emit("info", "Info 1")
        stream.emit("error", "Error 1")
        stream.emit("warning", "Warning 1")
        stream.emit("critical", "Critical 1")
        stream.emit("info", "Info 2")
        stream.emit("custom", "Custom 1")

        assert mock_logger.info.call_count == 3  # info, info, custom
        assert mock_logger.error.call_count == 2  # error, critical
        assert mock_logger.warning.call_count == 1

    def test_output_dir_attribute_accessible(self, tmp_path):
        """Test that output_dir attribute is accessible after init."""
        output_dir = tmp_path / "test_output"
        stream = EventStream(output_dir)

        assert hasattr(stream, "output_dir")
        assert stream.output_dir == output_dir

    @patch("configstream.event_stream.logger")
    def test_emit_with_none_message_converted_to_string(self, mock_logger, tmp_path):
        """Test emitting with message that gets stringified."""
        stream = EventStream(tmp_path)
        # Python will stringify these automatically
        stream.emit("info", str(None))

        mock_logger.info.assert_called_once()

    @patch("configstream.event_stream.logger")
    def test_emit_preserves_message_exactly(self, mock_logger, tmp_path):
        """Test that the message is preserved exactly as provided."""
        stream = EventStream(tmp_path)
        original_message = "  Spaced  Message  "
        stream.emit("info", original_message)

        expected_call = f"[info] {original_message}"
        mock_logger.info.assert_called_once_with(expected_call)

    @patch("configstream.event_stream.logger")
    def test_emit_with_json_like_message(self, mock_logger, tmp_path):
        """Test emitting JSON-like string messages."""
        stream = EventStream(tmp_path)
        json_message = '{"status": "ok", "count": 42}'
        stream.emit("info", json_message)

        mock_logger.info.assert_called_once_with(f"[info] {json_message}")

    @patch("configstream.event_stream.logger")
    def test_emit_with_sql_like_message(self, mock_logger, tmp_path):
        """Test emitting SQL-like string messages."""
        stream = EventStream(tmp_path)
        sql_message = "SELECT * FROM proxies WHERE status='active'"
        stream.emit("info", sql_message)

        mock_logger.info.assert_called_once_with(f"[info] {sql_message}")

    def test_multiple_stream_instances(self, tmp_path):
        """Test that multiple EventStream instances work independently."""
        dir1 = tmp_path / "stream1"
        dir2 = tmp_path / "stream2"

        stream1 = EventStream(dir1)
        stream2 = EventStream(dir2)

        assert stream1.output_dir != stream2.output_dir
        assert stream1.output_dir == dir1
        assert stream2.output_dir == dir2

    @patch("configstream.event_stream.logger")
    def test_emit_with_path_in_message(self, mock_logger, tmp_path):
        """Test emitting messages containing file paths."""
        stream = EventStream(tmp_path)
        path_message = "File saved to /tmp/output/proxy_list.txt"
        stream.emit("info", path_message)

        mock_logger.info.assert_called_once_with(f"[info] {path_message}")

    @patch("configstream.event_stream.logger")
    def test_emit_with_url_in_message(self, mock_logger, tmp_path):
        """Test emitting messages containing URLs."""
        stream = EventStream(tmp_path)
        url_message = "Fetching from https://example.com/api/proxies?format=json"
        stream.emit("info", url_message)

        mock_logger.info.assert_called_once_with(f"[info] {url_message}")

    def test_emit_persists_sanitized_jsonl(self, tmp_path):
        """EventStream persists sanitized JSONL event records."""
        stream = EventStream(tmp_path)
        stream.emit(
            "info",
            "Fetching https://example.com/sub?token=secret&id=123 from 203.0.113.8",
        )

        records = (
            (tmp_path / "pipeline_events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        assert len(records) == 1
        record = json.loads(records[0])
        assert record["event_type"] == "info"
        assert "secret" not in record["message"]
        assert "203.0.113.8" not in record["message"]
        assert "token=[MASKED]" in record["message"]
        assert "[IP]" in record["message"]
        assert record["timestamp"].endswith("+00:00")

    def test_emit_can_disable_jsonl_persistence(self, tmp_path):
        """Persistence can be disabled for tests or embedding contexts."""
        stream = EventStream(tmp_path, persist=False)
        stream.emit("info", "No file")

        assert not (tmp_path / "pipeline_events.jsonl").exists()
