# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import binascii
import logging
from typing import Optional

from ..constants import MAX_B64_INPUT_SIZE

logger = logging.getLogger(__name__)


def validate_b64_input(data: str) -> Optional[str]:
    """
    Validate base64 string before attempting decode.
    Optimized for single-pass processing to handle large payloads efficiently.
    """
    if not isinstance(data, str):
        return None

    # Fail Fast on HTML/JSON inputs
    if not data:
        return None

    s_stripped = data.lstrip()[:10]
    if s_stripped.startswith(("<", "{", "[")):
        return None

    trimmed = data.strip()
    if not trimmed:
        return None

    # Fix URL-encoded base64 (e.g., %3D, %2F)
    if "%" in trimmed:
        try:
            from urllib.parse import unquote

            unquoted = unquote(trimmed)
            if unquoted != trimmed:
                trimmed = unquoted
        except Exception:  # nosec
            pass

    # Basic char check + noise check
    # We allow some noise but if it's too much we drop it.
    valid_chars = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=-_\n\r \t"
    )

    # Immediate rejection for structural markers that indicate NOT Base64
    if ":" in trimmed and not trimmed.endswith("="):
        # Colon inside usually means method:password or something else
        # BUT standard base64 doesn't have colons.
        return None

    # Fast check for invalid chars
    invalid_chars = [c for c in trimmed if c not in valid_chars]
    if len(invalid_chars) > len(trimmed) * 0.05:  # >5% noise
        return None

    # Trim leading/trailing garbage while preserving internal separators
    start = 0
    end = len(trimmed)
    while start < end and trimmed[start] not in valid_chars:
        start += 1
    while end > start and trimmed[end - 1] not in valid_chars:
        end -= 1
    trimmed = trimmed[start:end]
    if not trimmed:
        return None

    # Normalize
    cleaned = "".join([c for c in trimmed if c in valid_chars and c not in "\n\r \t"])

    # Fix URL safe chars
    cleaned = cleaned.replace("-", "+").replace("_", "/")

    # Padding
    pad = len(cleaned) % 4
    if pad:
        cleaned += "=" * (4 - pad)

    return cleaned


def safe_b64_decode(data: str) -> Optional[str]:
    """
    Robustly decode Base64 strings, handling:
    - URL-safe characters (-_) vs Standard (+/)
    - Missing padding
    - Whitespace/Newlines
    - Mixed alphabets
    - Dirty inputs
    """
    if not data:
        return None
    if MAX_B64_INPUT_SIZE > 0 and len(data) > MAX_B64_INPUT_SIZE:
        return None

    # Use validate_b64_input for cleaning first
    cleaned = validate_b64_input(data)
    if not cleaned:
        return None

    try:
        # Validate=True to catch subtle corruptions
        return base64.b64decode(cleaned, validate=True).decode("utf-8", errors="ignore")
    except (binascii.Error, ValueError):
        # Fallback without validation if strict fails, but only if it looks plausible
        try:
            return base64.b64decode(cleaned, validate=False).decode(
                "utf-8", errors="ignore"
            )
        except Exception:  # nosec
            return None
