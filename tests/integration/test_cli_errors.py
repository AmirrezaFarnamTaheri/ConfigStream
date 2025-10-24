import pytest
from unittest.mock import patch, MagicMock
import sys
import json
from configstream.cli_errors import (
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


def test_custom_exceptions():
    assert CLIError("test").exit_code == 1
    assert FileError("test").exit_code == 2
    assert ConfigError("test").exit_code == 3
    assert DataError("test").exit_code == 4
    assert NetworkError("test").exit_code == 5


def test_format_error_message():
    assert "Test message" in format_error_message(CLIError("Test message"))
    assert "File not found" in format_error_message(FileNotFoundError("Test message"))
    assert "Test context" in format_error_message(CLIError("Test message"), context="Test context")
    try:
        raise CLIError("Test message")
    except CLIError as e:
        assert "Traceback" in format_error_message(e, include_traceback=True)


@patch("sys.exit")
@patch("builtins.print")
def test_handle_cli_error(mock_print, mock_exit):
    handle_cli_error(CLIError("Test message"))
    mock_exit.assert_called_with(1)
    handle_cli_error(FileError("Test message"))
    mock_exit.assert_called_with(2)
    handle_cli_error(Exception("Test message"))
    mock_exit.assert_called_with(1)


def test_safe_operation_success():
    def my_func():
        return "success"

    assert safe_operation(my_func) == "success"


@patch("sys.exit")
@patch("builtins.print")
def test_safe_operation_failure(mock_print, mock_exit):
    def my_func():
        raise ValueError("Test error")

    safe_operation(my_func)
    mock_exit.assert_called_with(1)


@patch("sys.exit")
@patch("builtins.print")
def test_safe_operation_keyboard_interrupt(mock_print, mock_exit):
    def my_func():
        raise KeyboardInterrupt

    safe_operation(my_func)
    mock_exit.assert_called_with(130)


@patch("sys.exit")
@patch("builtins.print")
def test_safe_operation_generic_exception(mock_print, mock_exit):
    def my_func():
        raise Exception("Generic error")

    safe_operation(my_func)
    mock_exit.assert_called_with(1)


@handle_cli_errors()
def decorated_function_success():
    return "success"


@handle_cli_errors()
def decorated_function_failure():
    raise ValueError("Test error")


@handle_cli_errors()
def decorated_function_file_not_found():
    raise FileNotFoundError("Test error")


@handle_cli_errors()
def decorated_function_json_decode_error():
    raise json.JSONDecodeError("Test error", "doc", 0)


@handle_cli_errors()
def decorated_function_connection_error():
    raise ConnectionError("Test error")


@handle_cli_errors(exit_on_keyboard_interrupt=False)
def decorated_function_keyboard_interrupt_no_exit():
    raise KeyboardInterrupt


@patch("sys.exit")
@patch("builtins.print")
def test_handle_cli_errors_decorator(mock_print, mock_exit):
    assert decorated_function_success() == "success"
    decorated_function_failure()
    mock_exit.assert_called_with(4)
    decorated_function_file_not_found()
    mock_exit.assert_called_with(2)
    decorated_function_json_decode_error()
    mock_exit.assert_called_with(3)
    decorated_function_connection_error()
    mock_exit.assert_called_with(5)
    with pytest.raises(KeyboardInterrupt):
        decorated_function_keyboard_interrupt_no_exit()


@patch("sys.exit")
@patch("builtins.print")
def test_error_context(mock_print, mock_exit):
    with ErrorContext():
        raise ValueError("Test error")
    mock_exit.assert_called_with(1)

    with ErrorContext():
        raise FileNotFoundError("Test error")
    mock_exit.assert_called_with(2)

    with ErrorContext():
        raise json.JSONDecodeError("Test error", "doc", 0)
    mock_exit.assert_called_with(3)

    with ErrorContext():
        raise KeyboardInterrupt
    mock_exit.assert_called_with(130)

    with ErrorContext(exit_on_error=False):
        with pytest.raises(CLIError):
            raise CLIError("test")

    with ErrorContext(exit_on_error=False) as ctx:
        assert ctx.__exit__(None, None, None) is False
