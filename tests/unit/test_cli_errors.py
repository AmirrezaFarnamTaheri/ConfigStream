import pytest
from configstream.cli_errors import handle_cli_errors, CLIError, ErrorContext


class CustomError(CLIError):
    pass


@handle_cli_errors()
def success_func():
    return "Success"


@handle_cli_errors()
def error_func():
    raise CustomError("Test Error")


@handle_cli_errors()
def unexpected_func():
    raise ValueError("Unexpected")


@handle_cli_errors()
def keyboard_func():
    raise KeyboardInterrupt()


def test_success():
    assert success_func() == "Success"


def test_cli_error_decorator(capsys):
    with pytest.raises(SystemExit) as exc:
        error_func()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Test Error" in captured.err


def test_unexpected_error_decorator(capsys):
    with pytest.raises(SystemExit) as exc:
        unexpected_func()
    assert exc.value.code == 4  # ValueError maps to 4 in cli_errors.py
    captured = capsys.readouterr()
    assert "Unexpected" in captured.err


def test_keyboard_interrupt_decorator(capsys):
    with pytest.raises(SystemExit) as exc:
        keyboard_func()
    assert exc.value.code == 130
    captured = capsys.readouterr()
    assert "cancelled" in captured.err


def test_error_context_success():
    with ErrorContext("Test Op"):
        pass


def test_error_context_failure(capsys):
    with pytest.raises(SystemExit):
        with ErrorContext("Test Op"):
            raise CLIError("Manual Error")
    captured = capsys.readouterr()
    assert "Manual Error" in captured.err
