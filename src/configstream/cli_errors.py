#!/usr/bin/env python3
"""Centralized error handling for CLI operations"""

from typing import Optional, Callable, Any, TypeVar
from functools import wraps
import sys
import logging
import json

logger = logging.getLogger(__name__)

# Type variable for decorator
F = TypeVar("F", bound=Callable[..., Any])


class CLIError(Exception):
    """Base exception for CLI operations."""

    exit_code = 1

    def __init__(self, message: str, context: Optional[str] = None):
        self.message = message
        self.context = context
        super().__init__(message)


class FileError(CLIError):
    """File operation error."""

    exit_code = 2


class ConfigError(CLIError):
    """Configuration error."""

    exit_code = 3


class DataError(CLIError):
    """Data processing error."""

    exit_code = 4


class NetworkError(CLIError):
    """Network operation error."""

    exit_code = 5


def format_error_message(
    error: Exception, context: Optional[str] = None, include_traceback: bool = False
) -> str:
    """
    Format error message for user display.

    Args:
        error: Exception that occurred
        context: Additional context about operation
        include_traceback: Whether to include full traceback

    Returns:
        Formatted error message string
    """
    error_types = {
        FileNotFoundError: "File not found",
        json.JSONDecodeError: "Invalid JSON",
        ValueError: "Invalid value",
        PermissionError: "Permission denied",
        TimeoutError: "Operation timeout",
        ConnectionError: "Connection failed",
        KeyboardInterrupt: "Operation cancelled",
    }

    error_name = error_types.get(type(error), type(error).__name__)

    if context:
        message = f"❌ {context}: {error_name}"
    else:
        message = f"❌ {error_name}"

    if str(error):
        message += f" - {str(error)}"

    if include_traceback:
        import traceback

        message += f"\n{traceback.format_exc()}"

    return message


def handle_cli_error(
    error: Exception,
    context: Optional[str] = None,
    exit_code: Optional[int] = None,
    verbose: bool = False,
) -> None:
    """
    Handle CLI error with consistent formatting and exit.

    Args:
        error: Exception that occurred
        context: Context about what was being done
        exit_code: Custom exit code (overrides default)
        verbose: Show full traceback
    """
    # Determine exit code
    if exit_code is None:
        if isinstance(error, CLIError):
            exit_code = error.exit_code
        else:
            exit_code = 1

    # Format and display message
    message = format_error_message(error, context, include_traceback=verbose)
    print(message, file=sys.stderr)

    # Log for debugging
    logger.debug(f"CLI Error: {message}", exc_info=verbose)

    sys.exit(exit_code)


def safe_operation(
    func: Callable[..., Any],
    *args: Any,
    context: str = "Operation",
    verbose: bool = False,
    **kwargs: Any,
) -> Any:
    """
    Execute a function with automatic error handling.

    Args:
        func: Function to execute
        *args: Positional arguments
        context: Context string for error messages
        verbose: Show detailed error info
        **kwargs: Keyword arguments

    Returns:
        Function result

    Raises:
        SystemExit: On error
    """
    try:
        return func(*args, **kwargs)
    except KeyboardInterrupt:
        handle_cli_error(
            CLIError("Operation cancelled by user"),
            context=context or "Operation",
            exit_code=130,
            verbose=verbose,
        )
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        PermissionError,
        TimeoutError,
        ConnectionError,
    ) as e:
        handle_cli_error(e, context=context, verbose=verbose)
    except Exception as e:
        handle_cli_error(e, context=context or "Unexpected error", exit_code=1, verbose=verbose)


def handle_cli_errors(
    context: str = "", exit_on_keyboard_interrupt: bool = True
) -> Callable[[F], F]:
    """
    Decorator to handle CLI errors automatically.

    Args:
        context: Context string for error messages
        exit_on_keyboard_interrupt: Exit on Ctrl+C (vs re-raise)

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                if exit_on_keyboard_interrupt:
                    print("\n⚠️  Operation cancelled by user", file=sys.stderr)
                    sys.exit(130)  # Standard SIGINT exit code
                else:
                    raise
            except CLIError as e:
                message = format_error_message(e, context or e.context)
                print(message, file=sys.stderr)
                sys.exit(e.exit_code)
            except (FileNotFoundError, PermissionError) as e:
                op_context = context or "File operation"
                message = format_error_message(e, op_context)
                print(message, file=sys.stderr)
                sys.exit(2)
            except json.JSONDecodeError as e:
                op_context = context or "Data processing"
                message = f"❌ {op_context}: Invalid JSON at line {e.lineno}: {e.msg}"
                print(message, file=sys.stderr)
                sys.exit(3)
            except (TimeoutError, ConnectionError) as e:
                op_context = context or "Network operation"
                message = format_error_message(e, op_context)
                print(message, file=sys.stderr)
                sys.exit(5)
            except ValueError as e:
                op_context = context or "Validation"
                message = format_error_message(e, op_context)
                print(message, file=sys.stderr)
                sys.exit(4)
            except Exception as e:
                op_context = context or "Operation"
                message = format_error_message(e, op_context, include_traceback=True)
                print(message, file=sys.stderr)
                sys.exit(1)

        return wrapper  # type: ignore

    return decorator


class ErrorContext:
    """Context manager for error handling."""

    def __init__(self, operation: str = "Operation", exit_on_error: bool = True):
        self.operation = operation
        self.exit_on_error = exit_on_error

    def __enter__(self) -> "ErrorContext":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is None:
            return False

        if isinstance(exc_val, KeyboardInterrupt):
            print(f"\n⚠️  {self.operation} cancelled by user", file=sys.stderr)
            if self.exit_on_error:
                sys.exit(130)
            return True

        message = format_error_message(exc_val, self.operation)
        print(message, file=sys.stderr)

        if self.exit_on_error:
            exit_code = 1
            if isinstance(exc_val, CLIError):
                exit_code = exc_val.exit_code
            elif isinstance(exc_val, (FileNotFoundError, PermissionError)):
                exit_code = 2
            elif isinstance(exc_val, json.JSONDecodeError):
                exit_code = 3

            sys.exit(exit_code)

        return True
