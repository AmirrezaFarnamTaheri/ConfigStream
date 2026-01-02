# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import binascii
import logging
import time
import threading
from collections import defaultdict
from typing import Optional, Dict

from ..constants import (
    MAX_B64_INPUT_SIZE,
    MAX_B64_OUTPUT_SIZE,
)

logger = logging.getLogger(__name__)

VALID_B64_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=-_\n\r \t"
)
# Valid chars excluding whitespace for stricter checking during cleaning
STRICT_B64_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=-_"
)


class RateLimitedLogger:
    """Helper to log warnings with rate limiting."""

    def __init__(self, threshold: int = 10, reset_interval: int = 60):
        self.threshold = threshold
        self.reset_interval = reset_interval
        self._lock = threading.Lock()
        self._counts: Dict[str, int] = defaultdict(int)
        self._last_reset = time.time()

    def warning(self, msg_type: str, message: str):
        """Log a warning if threshold not exceeded."""
        with self._lock:
            now = time.time()
            if now - self._last_reset > self.reset_interval:
                self._counts.clear()
                self._last_reset = now

            self._counts[msg_type] += 1
            count = self._counts[msg_type]

        if count <= self.threshold:
            logger.warning(message)
        elif count == self.threshold + 1:
            logger.warning(
                "%s: Further warnings suppressed (threshold: %d)",
                msg_type,
                self.threshold,
            )


# Global instance
_logger_limiter = RateLimitedLogger()


def validate_b64_input(data: str) -> Optional[str]:
    """Validate base64 string before attempting decode.
    Optimized for single-pass processing to handle large payloads efficiently.
    """
    if not isinstance(data, str):
        logger.warning(f"Expected string, got {type(data).__name__}")
        return None

    # [OPTIMIZATION] Fail Fast on HTML/JSON inputs
    # This prevents expensive iteration over 2MB error pages
    if not data:
        return None

    # Only check start/end on stripped data without creating full copy first if possible
    # But stripping is fast enough for 10 chars check
    s_stripped = data.lstrip()[:10]
    if s_stripped.startswith(("<", "{", "[")):
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

    length = len(trimmed)
    if length > MAX_B64_INPUT_SIZE:
        # [FIX] Reduce log severity for expected large payloads (e.g. huge lists)
        logger.debug(f"Base64 input too large: {length} bytes. treating as plain text.")
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
                length = len(trimmed)
        except Exception:
            pass

    # [FIX] Immediate rejection for structural markers that indicate NOT Base64
    # Colon ':' is strict forbidden in Base64 but standard in URLs/Configs
    if ":" in trimmed:
        return None

    # Single-pass validation and cleaning
    cleaned_chars = []
    invalid_count = 0
    threshold = int(length * 0.05)  # 5% threshold

    # Pre-allocate if possible? List append is efficient.

    for c in trimmed:
        if c in STRICT_B64_CHARS:
            # Normalize URL-safe chars on the fly
            if c == "-":
                cleaned_chars.append("+")
            elif c == "_":
                cleaned_chars.append("/")
            else:
                cleaned_chars.append(c)
        elif c in " \n\r\t":
            continue
        else:
            invalid_count += 1
            if invalid_count > threshold:
                # Early exit if noise is too high
                error_rate = invalid_count / length
                logger.debug(
                    "Skipping invalid base64 input (high noise ratio > %.2f%%): %d+ invalid chars.",
                    error_rate * 100,
                    invalid_count,
                )
                return None

    # Final check if we didn't exit early
    if invalid_count > 0:
        if length < 1000:
            logger.debug(
                f"Base64 input contained {invalid_count} invalid chars (cleaned). Context: {trimmed[:50]}..."
            )
        else:
            logger.warning(
                f"Base64 input contained {invalid_count} invalid chars (cleaned). Context: {trimmed[:50]}..."
            )

    cleaned = "".join(cleaned_chars)

    # Padding fix
    padding_needed = (4 - len(cleaned) % 4) % 4
    if padding_needed > 0:
        cleaned += "=" * padding_needed

    return cleaned


def safe_b64_decode(data: str) -> Optional[str]:
    """Safely decode base64 with comprehensive validation.

    NOTE: We perform a fast size check *before* any heavy processing to
    avoid memory pressure on extremely large payloads.
    """
    # Fast path: reject obviously oversized input before validation/decoding.
    if isinstance(data, str) and len(data) > MAX_B64_INPUT_SIZE:
        logger.error(
            f"Base64 input too large: {len(data)} bytes (max: {MAX_B64_INPUT_SIZE}) – skipping decode"
        )
        return None

    validated = validate_b64_input(data)
    if validated is None:
        # If validation fails, it's not base64. Return None to signal failure.
        return None

    # [FIX] Additional padding cleanup:
    # Some invalid base64 might have trailing garbage or already have padding that validate_b64_input didn't catch perfectly
    # if it mixed with other chars. Or sometimes existing padding is insufficient.
    # validate_b64_input adds padding, but let's double check before sending to b64decode
    # which is strict with validate=True.

    # Actually, validate_b64_input constructs 'cleaned' string which SHOULD be valid B64 chars only + padding.
    # However, sometimes excessive padding exists (e.g. '===') which b64decode hates.
    # Let's normalize padding: strip all '=' then add correct amount.

    validated = validated.rstrip("=")
    pad = len(validated) % 4
    if pad:
        validated += "=" * (4 - pad)

    try:
        decoded_bytes = base64.b64decode(validated, altchars=b"-_", validate=True)

        if len(decoded_bytes) > MAX_B64_OUTPUT_SIZE:
            logger.error(
                f"Decoded output too large: {len(decoded_bytes)} bytes (max: {MAX_B64_OUTPUT_SIZE})"
            )
            # If output is too large, it might be a valid decode but we reject it for safety.
            # Returning None is consistent with validation failure.
            return None

        try:
            return decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.debug("Decoded data is not valid UTF-8, trying latin-1")
            return decoded_bytes.decode("latin-1")
    except (binascii.Error, ValueError) as exc:
        # Many parsing failures are expected in mixed content. Lower log level to debug for common cases.
        if "Incorrect padding" in str(exc) or "Invalid base64-encoded string" in str(
            exc
        ):
            logger.debug(f"Base64 decode failed (expected for non-b64 content): {exc}")
        else:
            _logger_limiter.warning("base64_decode", f"Base64 decode failed: {exc}")

        # If decode fails, return None to signal it is not a valid base64 string
        return None
    except MemoryError:
        logger.error("Out of memory decoding base64")
        return None
    except Exception as exc:
        logger.error(f"Unexpected error decoding base64: {exc}")
        return None
