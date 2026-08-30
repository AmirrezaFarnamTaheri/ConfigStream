# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dependency-free sanitization for diagnostics and log messages."""

from __future__ import annotations

import re

_UUID_RE = re.compile(
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", re.IGNORECASE
)
_USERINFO_RE = re.compile(r"(?P<prefix>://[^/?#\s:@]+):([^/?#\s:@]+)@")
_INLINE_SECRET_USERINFO_RE = re.compile(
    r"(?i)\b(pass|password|token|secret|auth):([^@\s]+)@"
)
_QUERY_SECRET_RE = re.compile(
    r"(?i)(token|access_token|api_key|apikey|license_key|stego_key|config_stream_key|key|secret|pass|password|uuid|id|auth|authorization)=([^&\s]+)"
)
_AUTH_HEADER_RE = re.compile(
    r"(?i)(authorization|auth)\s*[:=]\s*(bearer|basic)?\s*([A-Za-z0-9\-._~+/]+=*)"
)
_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*")
_BASE64_RE = re.compile(r"\b[A-Za-z0-9+/]{20,}={0,2}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(r"\b(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b")


def sanitize_log_message(message: str, *, mask_patterns: bool = True) -> str:
    """Mask credentials and network identifiers without runtime dependencies."""
    if not mask_patterns:
        return message
    message = _UUID_RE.sub("[UUID]", message)
    message = _USERINFO_RE.sub(r"\g<prefix>:[MASKED]@", message)
    message = _INLINE_SECRET_USERINFO_RE.sub(r"\1:[MASKED]@", message)
    message = _QUERY_SECRET_RE.sub(r"\1=[MASKED]", message)
    message = _AUTH_HEADER_RE.sub(r"\1: [MASKED]", message)
    message = _BEARER_RE.sub("Bearer [MASKED]", message)
    message = _BASE64_RE.sub("[BASE64]", message)
    message = _IPV4_RE.sub("[IP]", message)
    return _IPV6_RE.sub("[IP]", message)
