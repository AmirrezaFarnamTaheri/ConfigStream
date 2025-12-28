from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Context variable for storing trace IDs across async contexts
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


# Use LogRecordFactory to ensure trace_id is ALWAYS present
_original_record_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):
    record = _original_record_factory(*args, **kwargs)
    # Ensure trace_id is always present
    trace_id = trace_id_var.get()
    record.trace_id = trace_id if trace_id else "-"
    return record


logging.setLogRecordFactory(_record_factory)


class TraceIdFilter(logging.Filter):
    """Deprecated: Logic moved to LogRecordFactory for robustness."""

    def filter(self, record: logging.LogRecord) -> bool:
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive information in log messages."""

    PATTERNS = {
        "uuid": r"(?:id|uuid|password|token)\s*[=:]\s*[a-f0-9\-]{16,}",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    }

    # URL pattern to detect and preserve URLs from masking
    URL_PATTERN = re.compile(r"https?://\S+")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        # Extract URLs and temporarily replace them with placeholders
        urls = []

        def url_replacer(match):
            urls.append(match.group(0))
            return f"__URL_PLACEHOLDER_{len(urls)-1}__"

        # Temporarily remove URLs
        message_without_urls = self.URL_PATTERN.sub(url_replacer, message)

        # Apply masking to non-URL content only
        message_without_urls = re.sub(
            self.PATTERNS["uuid"],
            "[MASKED_CREDENTIAL]",
            message_without_urls,
            flags=re.IGNORECASE,
        )
        message_without_urls = re.sub(
            self.PATTERNS["email"], "[MASKED_EMAIL]", message_without_urls
        )

        # Restore URLs
        for i, url in enumerate(urls):
            message_without_urls = message_without_urls.replace(
                f"__URL_PLACEHOLDER_{i}__", url
            )

        record.msg = message_without_urls
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
        if colour and sys.stdout.isatty():
            record.levelname = f"{colour}{record.levelname}{self.RESET}"
        return super().format(record)


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
        log_level: Legacy name for ``level`` (takes precedence when provided).
        format_style: "detailed" includes module/line, "simple" prints message.
        use_color: Force colour output. Defaults to auto-detect (TTY only).
        enable_trace_ids: Add trace IDs to log messages for request tracing.
    """
    effective_level = log_level or level
    log_level_value = _resolve_level(effective_level)

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

    # Apply sensitive data filter ONLY to console for security
    # File logs remain unmasked for debugging
    if mask_sensitive:
        console_handler.addFilter(SensitiveDataFilter())

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
        # NO masking filter for file handler - keep logs interpretable for debugging
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
        # NO masking filter for JSON logs - needed for log analysis tools
        root_logger.addHandler(json_file_handler)

    # Add trace ID filter (should be first for all handlers)
    if enable_trace_ids and not any(
        isinstance(existing, TraceIdFilter) for existing in root_logger.filters
    ):
        root_logger.addFilter(TraceIdFilter())

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
