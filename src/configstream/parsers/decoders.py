import base64
import binascii
import logging
import time
from collections import defaultdict
from typing import Optional, Dict

from ..constants import (
    MAX_B64_INPUT_SIZE,
    MAX_B64_OUTPUT_SIZE,
)

logger = logging.getLogger(__name__)

# Rate limit tracking for warnings
_warning_counts: Dict[str, int] = defaultdict(int)
_last_warning_reset = time.time()
_WARNING_THRESHOLD = 10  # Max warnings per type before suppression
_WARNING_RESET_INTERVAL = 60  # Reset counters every 60 seconds

VALID_B64_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=-_\n\r \t"
)


def _rate_limited_warning(msg_type: str, message: str):
    """Log a warning with rate limiting to avoid log spam."""
    global _last_warning_reset

    # Reset counters periodically
    now = time.time()
    if now - _last_warning_reset > _WARNING_RESET_INTERVAL:
        _warning_counts.clear()
        _last_warning_reset = now

    _warning_counts[msg_type] += 1
    if _warning_counts[msg_type] <= _WARNING_THRESHOLD:
        logger.warning(message)
    elif _warning_counts[msg_type] == _WARNING_THRESHOLD + 1:
        logger.warning(
            f"{msg_type}: Further warnings suppressed (threshold: {_WARNING_THRESHOLD})"
        )


def validate_b64_input(data: str) -> Optional[str]:
    """Validate base64 string before attempting decode."""
    if not isinstance(data, str):
        logger.warning("Expected string, got %s", type(data).__name__)
        return None

    # Handle comments starting with '#' or space-separated remarks
    # Split by '#' first (common comment delimiter)
    if "#" in data:
        data = data.split("#", 1)[0]

    # Heuristic: If we have spaces, it might be "BASE64 REMARK".
    # Standard Base64 does not contain spaces.
    # We take the first part.
    if data and not data.isspace():
        parts = data.split(None, 1)
        if parts:
            data = parts[0]

    trimmed = data.strip()
    if not trimmed:
        logger.debug("Empty base64 input")
        return None

    if len(trimmed) > MAX_B64_INPUT_SIZE:
        logger.error(
            "Base64 input too large: %s bytes (max: %s)",
            len(trimmed),
            MAX_B64_INPUT_SIZE,
        )
        return None

    # Auto-fix URL-encoded base64 (e.g., %3D, %2F)
    if "%" in trimmed:
        try:
            from urllib.parse import unquote

            unquoted = unquote(trimmed)
            # Only use unquoted version if it actually changed and looks valid
            if unquoted != trimmed:
                logger.debug("Auto-fixed URL-encoded base64 input")
                trimmed = unquoted
        except Exception:
            pass

    invalid_chars = set(trimmed) - VALID_B64_CHARS

    # [FIXED LOGIC] If there are too many invalid characters, it's likely not base64 at all.
    # Return None silently or with debug to avoid log spam.
    if invalid_chars:
        error_rate = len(invalid_chars) / len(trimmed)
        if (
            error_rate > 0.05
        ):  # >5% invalid chars -> definitely not base64 (probably HTML or text)
            logger.debug(
                "Skipping invalid base64 input (high noise ratio: %.2f%%): %d invalid chars. First 10: %s",
                error_rate * 100,
                len(invalid_chars),
                list(invalid_chars)[:10],
            )
            return None

        # Don't log warning if it's just a config line trying to be decoded as base64
        if len(trimmed) < 1000:
            logger.debug(
                "Invalid base64 characters in short string: %s. Context: %s...",
                invalid_chars,
                trimmed[:50],
            )
        else:
            logger.warning(
                "Invalid base64 characters: %s in payload starting with: %s...",
                invalid_chars,
                trimmed[:50],
            )
        return None

    cleaned = "".join(c for c in trimmed if c not in " \n\r\t")
    padding_needed = (4 - len(cleaned) % 4) % 4
    if padding_needed > 0:
        cleaned += "=" * padding_needed

    return cleaned


def safe_b64_decode(data: str) -> str:
    """Safely decode base64 with comprehensive validation.

    NOTE: We perform a fast size check *before* any heavy processing to
    avoid memory pressure on extremely large payloads.
    """
    # Fast path: reject obviously oversized input before validation/decoding.
    if isinstance(data, str) and len(data) > MAX_B64_INPUT_SIZE:
        logger.error(
            "Base64 input too large: %s bytes (max: %s) – skipping decode",
            len(data),
            MAX_B64_INPUT_SIZE,
        )
        return data

    validated = validate_b64_input(data)
    if validated is None:
        return data

    try:
        decoded_bytes = base64.b64decode(validated, validate=True)

        if len(decoded_bytes) > MAX_B64_OUTPUT_SIZE:
            logger.error(
                f"Decoded output too large: {len(decoded_bytes)} bytes (max: {MAX_B64_OUTPUT_SIZE})"
            )
            return data

        try:
            return decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.debug("Decoded data is not valid UTF-8, trying latin-1")
            return decoded_bytes.decode("latin-1")
    except (binascii.Error, ValueError) as exc:
        _rate_limited_warning("base64_decode", f"Base64 decode failed: {exc}")
        return data
    except MemoryError:
        logger.error("Out of memory decoding base64")
        return data
    except Exception as exc:
        logger.error("Unexpected error decoding base64: %s", exc)
        return data
