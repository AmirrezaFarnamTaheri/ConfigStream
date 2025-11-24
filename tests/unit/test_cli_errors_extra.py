"""Tests for CLI errors module."""

import pytest
import sys
import json
from unittest.mock import patch, MagicMock
from io import StringIO
from src.configstream.cli_errors import (
    CLIError,
    FileError,
    ConfigError,
    DataError,
    NetworkError,
    format_error_message,
    handle_cli_error,
    safe_operation,
    handle_cli_errors,
    ErrorContext,
)


def test_exception_types():
    assert CLIError("msg").exit_code == 1
    assert FileError("msg").exit_code == 2
    assert ConfigError("msg").exit_code == 3
    assert DataError("msg").exit_code == 4
    assert NetworkError("msg").exit_code == 5


def test_format_error_message():
    # Simple error
    msg = format_error_message(ValueError("Invalid"), "Context")
    assert "Context" in msg
    assert "Invalid value" in msg
    assert "- Invalid" in msg

    # No context
    msg = format_error_message(ValueError("Invalid"))
    assert "Invalid value" in msg

    # Traceback
    # Traceback is only available if exception was raised in a try/except or manually set
    try:
        raise ValueError("Invalid")
    except ValueError as e:
        msg = format_error_message(e, include_traceback=True)
        assert "Traceback" in msg


def test_handle_cli_error():
    with (
        patch("sys.exit") as mock_exit,
        patch("sys.stderr", new_callable=StringIO) as stderr,
    ):
        handle_cli_error(CLIError("Boom"), exit_code=99)
        mock_exit.assert_called_with(99)
        assert "Boom" in stderr.getvalue()

    # Default exit code
    with patch("sys.exit") as mock_exit:
        handle_cli_error(ValueError("Bad"))
        mock_exit.assert_called_with(1)

    # From exception
    with patch("sys.exit") as mock_exit:
        handle_cli_error(FileError("Bad"))
        mock_exit.assert_called_with(2)


def test_safe_operation():
    # Success
    assert safe_operation(lambda x: x + 1, 1) == 2

    # Failure handled
    with patch("sys.exit") as mock_exit:
        # We need a lambda that raises an exception
        def raise_val():
            raise ValueError("Bad")

        safe_operation(raise_val)
        mock_exit.assert_called_with(
            1
        )  # Default for generic exception unless typed (ValueError logic inside handles it)
        # ValueError is handled by handle_cli_error. But safe_operation catches ValueError and calls handle_cli_error without explicit exit_code override, so it defaults to 1?
        # Let's check handle_cli_error logic:
        # if exit_code is None: if CLIError -> use it. else -> 1.
        # Wait, safe_operation catches specific errors and calls handle_cli_error.
        # It doesn't pass exit_code for them.
        # But handle_cli_error defaults to 1 for non-CLIErrors.

    # Keyboard Interrupt
    with patch("sys.exit") as mock_exit:

        def raise_kb():
            raise KeyboardInterrupt

        safe_operation(raise_kb)
        mock_exit.assert_called_with(130)


def test_decorator_handle_cli_errors():
    @handle_cli_errors(context="Test")
    def fail(exc):
        raise exc

    # CLIError
    with patch("sys.exit") as mock_exit:
        fail(CLIError("Boom"))
        mock_exit.assert_called_with(1)

    # JSON Error
    with patch("sys.exit") as mock_exit:
        fail(json.JSONDecodeError("msg", "doc", 1))
        mock_exit.assert_called_with(3)

    # Keyboard
    with patch("sys.exit") as mock_exit:
        fail(KeyboardInterrupt)
        mock_exit.assert_called_with(130)

    # Re-raise Keyboard
    @handle_cli_errors(exit_on_keyboard_interrupt=False)
    def fail_kb():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        fail_kb()


def test_error_context():
    # Context handled
    with patch("sys.exit") as mock_exit:
        with ErrorContext("Ctx"):
            raise ValueError("Boom")
        mock_exit.assert_called_with(1)

    # Suppress exit
    with ErrorContext("Ctx", exit_on_error=False):
        raise ValueError("Boom")  # Should not exit

    # Keyboard
    with patch("sys.exit") as mock_exit:
        with ErrorContext("Ctx"):
            raise KeyboardInterrupt
        mock_exit.assert_called_with(130)

    # Keyboard suppressed
    with patch("sys.exit") as mock_exit:
        with ErrorContext("Ctx", exit_on_error=False):
            raise KeyboardInterrupt  # Should print but not exit
        mock_exit.assert_not_called()

    # No exception
    with ErrorContext("Ctx"):
        pass

    # Coverage for logic
    with patch("sys.exit") as mock_exit:
        with ErrorContext("Ctx"):
            raise FileNotFoundError("Missing")
        mock_exit.assert_called_with(2)
