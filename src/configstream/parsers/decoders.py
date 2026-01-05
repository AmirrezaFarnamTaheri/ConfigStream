# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import binascii
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def validate_b64_input(data: str) -> Optional[str]:
    """
    Validate base64 string before attempting decode.
    Legacy wrapper around safe_b64_decode's internal logic if needed,
    but safe_b64_decode handles everything now.
    """
    if not data:
        return None
    # This is a stub for backward compatibility if other modules use it directly.
    # But ideally, logic is now inside safe_b64_decode or we keep the old logic?
    # The new robust logic is better.
    return data

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

    # 1. Clean payload: remove whitespace/newlines
    data = re.sub(r'\s+', '', data)

    if not data:
        return None

    # Helper to attempt decode
    def try_decode(s: str, altchars=None) -> Optional[str]:
        # Fix padding
        pad = len(s) % 4
        if pad:
            s += '=' * (4 - pad)
        try:
            return base64.b64decode(s, altchars=altchars, validate=False).decode('utf-8', errors='ignore')
        except (binascii.Error, ValueError):
            return None

    # 2. Try Standard Decode
    res = try_decode(data)
    if res: return res

    # 3. Try URL-Safe Decode (explicit replacement)
    res = try_decode(data.replace('-', '+').replace('_', '/'))
    if res: return res

    # 4. Try URL-Safe Decode (using altchars arg)
    res = try_decode(data, altchars=b'-_')
    if res: return res

    return None
