# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import logging
import re
import sys
import uuid
import json
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .security_validator import SecurityValidator

# Context variable for storing trace IDs across async contexts
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


# Attribute used to mark a factory we installed, so install_trace_id_factory()
# is idempotent and never wraps our own factory repeatedly (which would grow an
# unbounded chain on repeated setup_logging calls).
_FACTORY_INSTALLED_ATTR = "_configstream_trace_id_factory"


def _make_record_factory(original_factory):
    """Build a LogRecordFactory that always attaches a ``trace_id`` attribute."""

    def _record_factory(*args, **kwargs):
        record = original_factory(*args, **kwargs)
        trace_id = trace_id_var.get()
        record.trace_id = trace_id if trace_id else "-"
        return record

    setattr(_record_factory, _FACTORY_INSTALLED_ATTR, True)
    return _record_factory


def install_trace_id_factory() -> None:
    """
    Install the trace-id LogRecordFactory (idempotent).

    Done lazily from :func:`setup_logging` rather than at import time so that
    importing this module has no global side effect on the logging subsystem;
    repeated calls are safe and will not chain factories.
    """
    current = logging.getLogRecordFactory()
    if getattr(current, _FACTORY_INSTALLED_ATTR, False):
        return
    logging.setLogRecordFactory(_make_record_factory(current))


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive information in log messages.

    The previous implementation extracted URLs *before* masking secrets,
    which meant credentials embedded in URLs (e.g., vless://uuid@host,
    https://api.service.com?token=secret) were whitelisted from redaction.
    Now we apply masking to the ENTIRE string first, including URL contents.
    """

    # Pre-compiled patterns for per-message hot path
    _CREDENTIAL_PATTERN = re.compile(
        r"(?:id|uuid|password|token)\s*[=:]\s*[a-f0-9\-]{16,}",
        re.IGNORECASE,
    )
    _EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    # Pattern for standalone UUIDs (common in proxy URIs)
    UUID_PATTERN = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.IGNORECASE,
    )

    # Pattern for tokens/secrets in query strings
    QUERY_SECRET_PATTERN = re.compile(
        r"((?:token|key|secret|password|auth|apikey)=)([^&\s]+)",
        re.IGNORECASE,
    )

    # Pattern for userinfo in URLs (user:pass@host)
    USERINFO_PATTERN = re.compile(r"://([^@/\s]+)@")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        # Apply ALL masking patterns to the ENTIRE string (including URLs)
        # 1. Mask credentials in key=value patterns
        message = self._CREDENTIAL_PATTERN.sub("[MASKED_CREDENTIAL]", message)
        # 2. Mask emails
        message = self._EMAIL_PATTERN.sub("[MASKED_EMAIL]", message)
        # 3. Mask standalone UUIDs (proxy credentials)
        message = self.UUID_PATTERN.sub("[MASKED_UUID]", message)
        # 4. Mask query string secrets
        message = self.QUERY_SECRET_PATTERN.sub(r"\1[MASKED]", message)
        # 5. Mask userinfo in URLs (user:pass@host -> [MASKED]@host)
        message = self.USERINFO_PATTERN.sub("://[MASKED]@", message)
        # 6. Escape newlines to prevent log injection
        message = message.replace("\n", "\\n").replace("\r", "\\r")

        # Final pass through SecurityValidator for additional sanitization
        record.msg = SecurityValidator.sanitize_log_message(message)
        record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    """Formats log records as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
            "location": f"{record.filename}:{record.lineno}",
        }
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_object)


class ColoredFormatter(logging.Formatter):
    """Formatter that adds ANSI colours for terminal output."""

    COLOURS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self.COLOURS.get(record.levelno, "")
        original_levelname = record.levelname
        if colour and sys.stdout.isatty():
            record.levelname = f"{colour}{record.levelname}{self.RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname


def _resolve_level(level: str) -> int:
    """Convert string level names to logging constants."""
    try:
        value = getattr(logging, level.upper())
        if isinstance(value, int):
            return value
    except AttributeError:
        return logging.INFO
    return logging.INFO


def setup_logging(
    level: str = "INFO",
    mask_sensitive: bool = True,
    log_level: Optional[str] = None,
    *,
    log_file: Optional[str | Path] = "configstream.log",
    json_log_file: Optional[str | Path] = None,
    format_style: str = "detailed",
    use_color: Optional[bool] = None,
    enable_trace_ids: bool = True,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        mask_sensitive: Apply masking filter for secrets.
        log_file: Optional log file path; pass None to disable file logging.
        log_level: Alias for ``level`` (takes precedence when provided).
        format_style: "detailed" includes module/line, "simple" prints message.
        use_color: Force colour output. Defaults to auto-detect (TTY only).
        enable_trace_ids: Add trace IDs to log messages for request tracing.
    """
    effective_level = log_level or level
    log_level_value = _resolve_level(effective_level)

    if enable_trace_ids:
        install_trace_id_factory()

    if format_style == "detailed":
        if enable_trace_ids:
            fmt = (
                "%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - "
                "[%(filename)s:%(lineno)d] - %(message)s"
            )
        else:
            fmt = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "[%(filename)s:%(lineno)d] - %(message)s"
            )
    else:
        if enable_trace_ids:
            fmt = "%(levelname)s - [%(trace_id)s] - %(message)s"
        else:
            fmt = "%(levelname)s - %(message)s"

    colour_output = use_color if use_color is not None else sys.stdout.isatty()

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_value)
    root_logger.handlers.clear()

    formatter = ColoredFormatter(fmt) if colour_output else logging.Formatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_value)
    console_handler.setFormatter(formatter)

    # Apply sensitive data filter to all handlers for security.
    # File logs will be masked by default.
    if mask_sensitive:
        data_filter = SensitiveDataFilter()
        console_handler.addFilter(data_filter)

    root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Use RotatingFileHandler to prevent log files from growing too large
        # Max size: 10MB, keep 5 backup files
        file_handler = RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(log_level_value)
        file_handler.setFormatter(logging.Formatter(fmt))
        # Apply masking filter to file handler
        if mask_sensitive:
            file_handler.addFilter(data_filter)
        root_logger.addHandler(file_handler)

    if json_log_file:
        json_log_path = Path(json_log_file)
        json_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Use RotatingFileHandler for JSON logs as well
        json_file_handler = RotatingFileHandler(
            json_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        json_file_handler.setLevel(log_level_value)
        json_file_handler.setFormatter(JsonFormatter())
        # Apply masking filter to JSON logs
        if mask_sensitive:
            json_file_handler.addFilter(data_filter)
        root_logger.addHandler(json_file_handler)

    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """
    Set a trace ID for the current context.

    Args:
        trace_id: Optional trace ID. If None, generates a new one.

    Returns:
        The trace ID that was set.
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())[:8]
    else:
        # Sanitize: allow only alphanumerics and dash/underscore, cap length
        safe = "".join(c for c in str(trace_id) if c.isalnum() or c in "-_")[:32]
        trace_id = safe if safe else "-"
    trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> str:
    """Get the current trace ID, or empty string if not set."""
    return trace_id_var.get()


def clear_trace_id() -> None:
    """Clear the trace ID for the current context."""
    trace_id_var.set("")
