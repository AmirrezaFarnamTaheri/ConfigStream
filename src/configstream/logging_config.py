from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive information in log messages."""

    PATTERNS = {
        "uuid": r"(?:id|uuid|password|token)\s*[=:]\s*[a-f0-9\-]{16,}",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        message = re.sub(self.PATTERNS["uuid"], "[MASKED_CREDENTIAL]", message, flags=re.IGNORECASE)
        message = re.sub(self.PATTERNS["email"], "[MASKED_EMAIL]", message)

        record.msg = message
        return True


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
    format_style: str = "detailed",
    use_color: Optional[bool] = None,
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
    """
    effective_level = log_level or level
    log_level_value = _resolve_level(effective_level)

    if format_style == "detailed":
        fmt = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
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
    root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(log_level_value)
        file_handler.setFormatter(logging.Formatter(fmt))
        root_logger.addHandler(file_handler)

    if mask_sensitive and not any(
        isinstance(existing, SensitiveDataFilter) for existing in root_logger.filters
    ):
        root_logger.addFilter(SensitiveDataFilter())

    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
